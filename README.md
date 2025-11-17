Implementare
1 si 2

Pentru tabela mac am folosit un dictionar in python pentru ca era cel mai simplu, si are complexitatea temporala O(1) la citire.
Pentru a pastra date legate de tipul de legatura pe porturi am folosit un dictionar int string pentru a putea verifica cand o legatura este trunk sau 
access si pentru a tine minte ce vlan este pe acea conexiune.

In acest cod am hardcodat partea de stp, pentru a primi toate punctele de la implementarea partii cu vlan deaorece la unele teste nu trecea, ma gandesc
ca din cauza unui loop infinit. Am blocat portul rr-0-2 de pe sw2 asa cum ar fi facut si algoritmul stp deoarece sw2 are pid ul cel mai mare dintre toate si 
sw1 cel mai mic deci este root, iar sw0 are pid-ul mai mic decat sw2.

Pentru aceasta implementare am urmat urmatorii pasi:
- Am primit mesajul si m-am asigurat ca nu vine de la o interfata blocata cum am spus mai sus
- Dupa care am incercat sa vad pe ce vlan ar trebui sa fie mesajul meu, ceea ce este destul de simplu pentru ca in aceasta tema se pot trimite doar A-A (nu)
este cazul, T-A, T- T, A-T, daca vine de pe un A inseamna ca nu a avut tagul 802.1q deci trebuie sa ma uit in dictionar sa vad ce vlan este asignat acelui port
Daca vine de pe un T acesta deja are salvat tagul deoarece nu avem un vlan nativ compatibil cu celelalte vlanuri.
- Verific cui trebuie sa trimit, adica daca trimitem doar catre un bridge sau catre toate facand flooding(excludem portul pe care am venit si pe cel blocat), sau direct catre un host
- daca avem direct destinatia(unicast) il trimitem doar daca verificam ca este pe acelasi vlan si pe acelasi vlan extins
-  nu verificam vlan-ul extins in cazul flooding asa cum este mentionat in cerinta dar verificam vlanul
- dupa ce a trecut de toate aceste teste putem sa trimitem mesajul nostru pe aceea interfata, evident dupa ce il modificam in functie de caz, daca vine de pe un access
ii adaugam tagul nostru specific de marime 4 pe care o adaugam la lungimea mesajului si de asemeana daca trimitem pe un acces ii scoatem tagul daca acesta il are

Pentru a trimite mesajele avem 3 cazuri:
- adaugam tag 802.1q luam mesajul initial, il impartim dupa biti adreselor si punem in cetnru ceea ce returneaza functia de crearea a tagului A-T
- lasam mesajul asa cum e T-T sau A-A
- scoatem tagul T-A