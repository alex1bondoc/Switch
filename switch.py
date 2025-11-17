#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]

    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    vlan_tci = -1
    # Check for VLAN tag (0x8200 in network byte order is b'\x82\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id, vlan_tci

def create_vlan_tag(ext_id, vlan_id):
    # Use EtherType = 8200h for our custom 802.1Q-like protocol.
    # PCP and DEI bits are used to extend the original VID.
    #
    # The ext_id should be the sum of all nibbles in the MAC address of the
    # host attached to the _access_ port. Ignore the overflow in the 4-bit
    # accumulator.
    #
    # NOTE: Include these 4 extensions bits only in the check for unicast
    #       frames. For multicasts, assume that you're dealing with 802.1Q.
    return struct.pack('!H', 0x8200) + \
           struct.pack('!H', ((ext_id & 0xF) << 12) | (vlan_id & 0x0FFF))

def function_on_different_thread():
    while True:
        time.sleep(1)


def main():
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)
    # citim din config porturile
    f = open("configs/switch{}.cfg".format(switch_id), "r")
    lines = f.readlines()
    f.close()
    # dictionar de la int la string pentru a pastra date despre porturi si tipul lor
    ports = {}
    for i in range(1, len(lines)):
        sep = lines[i].split()
        ports[i] = sep[1].strip()
    #tabela mac tot dictionar
    mac = {}

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # Example of running a function on a separate thread.
    t = threading.Thread(target=function_on_different_thread)
    t.start()
    #interfetele switchurilor
    for i in interfaces:
        print(get_interface_name(i))

    # hardcodare pentru a face arborele din stp pentru a trece testele de la vlan
    block_interface = -1
    stop_search = 1
    if switch_id == "2":
        for i in interfaces:
            if stop_search == 1:
                if get_interface_name(i) == "rr-0-2":
                    block_interface = i
                    stop_search = 0

    while True:
        interface, data, length = recv_from_any_link()
        # nu permitem frame-uri de pe portul blocat
        if interface == block_interface:
            continue

        dest_mac, src_mac, ethertype, vlan_id, vlan_tci = parse_ethernet_header(data)
        
        # Calculam inline suma nibble-urilor pentru source MAC (folosit la get_exit_id_mac)
        nibble_src = sum(byte // 16 + byte %16 for byte in src_mac) & 0x0f

        #verificam daca este trunk sau acces deoarece ne dam seama pe ce vlan mergem acum
        # daca e trunk avem in vlan_id id ul vlanului iar daca nu inseamna ca a venit de pe access
        # deci trebuie sa luam din dictionar vlanul
        interface_name = get_interface_name(interface)
        current_vlan = 0
        if ports[interface + 1] == 'T':
            current_vlan = vlan_id
        else:
            current_vlan = int(ports[interface + 1])
        #aici verificam pe ce vlan extins operam deaorece daca mergem pe un trunk avem asta in tci-ul frame-ului
        #daca nu avem nibble ul hostului calculat mai sus
        curr_nibble = 0
        if ports[interface + 1] == 'T':
            curr_nibble = (vlan_tci >> 12) & 0xF
        else:
            curr_nibble = nibble_src

        # Print formatting
        dest_mac_print = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac_print = ':'.join(f'{b:02x}' for b in src_mac)

        print(f'Destination MAC: {dest_mac_print}')
        print(f'Source MAC: {src_mac_print}')
        print(f'EtherType: {ethertype}')
        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # actualizam intrarea in tabela cam (proces de memorare)
        mac[src_mac] = interface
        # verificam daca e unicast prin paritatea primului bit in adresa mac a destinatiei
        dest_ports = []

        # daca e unicast vom trimite doar pe un port daca nu vom face flooding 
        #trimitem pe porturi mai putin pe cel blocat la stp si pe cel pe care a venit
        if dest_mac[0] & 1 == 0:
            if dest_mac in mac:
                dest_ports.append(mac[dest_mac])
            else:
                for p in interfaces:
                    if p != interface:
                        dest_ports.append(p)
        else:
            for p in interfaces:
                if p != interface :
                    dest_ports.append(p)
        
        for out_port in dest_ports:    
            # nu trimitem pe portul blocat
            if out_port == block_interface:
                continue
            out_interface_name = get_interface_name(out_port)
            #fac dupa pseudocodul din pdf
            if dest_mac[0] & 1 == 0 and dest_mac in mac:
                # daca trimitem pe un trunk trimitem orice ar fi
                if ports[out_port+1] == 'T':
                    if vlan_id == -1 :
                        vlan_tag = create_vlan_tag(nibble_src, current_vlan)
                        send_to_link(out_port, length + 4, data[0:12] + vlan_tag + data[12:])
                    else :
                        send_to_link(out_port, length, data)
                else:
                    #verificam daca sunt in acelasi vlan
                    if current_vlan == int(ports[out_port+1]):
                        nibble_dest = sum(x // 16 + x %16 for x in dest_mac) & 0x0f
                        # verificam daca sun in acelasi vlan extins cu nibble
                        if curr_nibble == nibble_dest:
                            send_to_link(out_port, length-4, data[0:12] + data[16:])
            else:
                #daca facem flooding trimitem pe tot ce e trunk si altfel trimitem doar pe cele din acelasi vlan cu noi
                if ports[out_port+1] == 'T':
                    mac_header = data[0:12]
                    if vlan_id == -1 :
                        vlan_tag = create_vlan_tag(nibble_src, current_vlan)
                        send_to_link(out_port, length + 4, data[0:12] + vlan_tag + data[12:])
                    else :
                        send_to_link(out_port, length, data)
                else:
                    if current_vlan == int(ports[out_port+1]):
                        send_to_link(out_port, length-3, data[0:12]+data[16:])
            # sleep pus dupa trimitere la recomandarea de pe forum                    
            time.sleep(0.5)

if __name__ == "__main__":
    main()