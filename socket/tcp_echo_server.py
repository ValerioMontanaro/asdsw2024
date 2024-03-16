import socket
from sys import argv
import time 

# i socket servono in generale per far comunicare macchine diverse quindi applicazioni diverse

localIP     = argv[1]
localPORT   = int(argv[2])

# Solo per definire  il tipo di socket
TCPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

# operazione di bind per associare il socket ad un indirizzo IP e una porta
TCPServerSocket.bind((localIP, localPORT))

print('TCP Server UP ({},{}), waiting for connections ...'.format(localIP, localPORT))

# mi metto in ascolto
TCPServerSocket.listen()

# Accetto una nuova connessione
# conn è il socket che mi serve per comunicare con il client
# addr punta a una tupla che contiene l'indirizzo del client e la porta del client 
conn, addr = TCPServerSocket.accept()

print('Client: {}'.format(addr))

# Un po' di attesa per dare tempo al client di connettersi 
time.sleep(1)
while True:
    # ricevo i dati dal client e li salvo in data che è una stringa di byte (1024)
    data = conn.recv(1024)

    # Se non ci sono più dati da ricevere esco dal ciclo ma per fare ciò devo chiudere la connessione e quindi chiudere il terminale del client
    if not data:
        break

    #print('{}: echo message: {}'.format(addr, data[:-1].decode('utf-8')))
    # Stampo l'indirizzo del client e il messaggio che mi ha inviato 
    print('{}: echo message: {}'.format(addr, data))
    
    # Invio i dati al client 
    conn.sendall(data)

# Chiudo la connessione in essere
conn.close()


TCPServerSocket.close()