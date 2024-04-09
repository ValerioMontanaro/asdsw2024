import socket
from sys import argv
import logging
import re
import json

# decodifica il messaggio di join ricevuto dal nodo
def decodeJoin(addr, mess):
    # Va a cercare la presenza di un json nel messaggio
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\, ]*\})' , mess)
    # se bool(result) è True allora c'è un json nel messaggio
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))
        # prende il primo gruppo di result che è il json e lo salva in action, questo json contiene le informazioni del nodo che vuole fare join come porta e indirizzo del nodo che vuole fare join
        action = json.loads(result.group(1))
    else:
        action = {}
    
    # aggiunge il comando join all'azione che è un dizionario 
    action['command'] = 'join'

    return action

def decodeLeave(addr, mess):
    # Va a cercare la presenza di un json nel messaggio
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\, ]*\})' , mess)
    # se bool(result) è True allora c'è un json nel messaggio
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))
        # prende il primo gruppo di result che è il json e lo salva in action, questo json contiene le informazioni del nodo che vuole fare leave come porta e indirizzo del nodo che vuole fare leave
        action = json.loads(result.group(1))
    else:
        action = {}

    # aggiunge il comando leave all'azione che è un dizionario
    action['command'] = 'leave'
    
    return action

def decodeMessage(addr, mess):
    # Cerca la presenza di un comando nel messaggio che è tra parentesi quadre in maiuscolo e salva i risultati in result che è un oggetto di tipo re.Match 
    # cioè un oggetto che contiene le informazioni sulle corrispondenze trovate, queste informazioni sono i gruppi di corrispondenza trovati nel messaggio
    result = re.search('^\[([A-Z]*)\]' , mess)
    # se bool(result) è True allora c'è un comando nel messaggio
    if bool(result):
        # prende il primo gruppo di result che è il comando e lo salva in command 
        command = result.group(1)
        # stampa il comando
        logging.debug('COMMAND: {}'.format(command))

        '''
        if command == 'JOIN':
            decodeJoin(addr, mess)
        else if command == 'LEAVE':
            decodeLEAVE(addr, mess)
        '''

        # cerca il comando tra i comandi possibili e chiama la funzione corrispondente al comando passandogli l'indirizzo e il messaggio
        try:
            # in parentesi graffe definisco un dizionario con chiave il comando e valore la funzione da chiamare con 2 parametri
            # poi costruisco il dizionario con il comando command come chiave e la funzione come valore e chiamo la funzione passandogli i parametri addr e mess
            action = {
                'JOIN'  : lambda param1,param2 : decodeJoin(param1, param2),
                'LEAVE' : lambda param1,param2 : decodeLeave(param1, param2)
            }[command](addr, mess)
        except:
            action = {}
            action['command'] = 'unknown'
    else:
        action = {}
        action['command'] = 'invalid'    

    logging.debug('ACTION: {}'.format(action))

    return action

def updateRingJoin(action, listOfNodes):
    # deve aggiungere un nodo alla lista di nodi
    logging.debug('RING JOIN UPDATE')
    # creo un dizionario vuoto che rappresenta il nodo che vuole fare join 
    node = {}

    id_ = 1
    # prendo tutti gli id dei nodi presenti nella lista di nodi e li metto in una lista
    idList = [int(eNode['id']) for eNode in listOfNodes]
    # faccio un ciclo da 1 a len(listOfNodes)+2 e se l'id non è presente nella lista di id dei nodi allora lo salvo in id_ ed esco dal ciclo 
    for i in range(1, len(listOfNodes)+2):
        if i not in idList:
            id_ = i
            break
    
    node['id']   = str(id_)
    node['port'] = action['port']
    node['addr'] = action['addr']

    # Verifica esistenza nodo che vuole aggiungersi nella lista di nodi esistente e se non esiste già lo aggiunge alla lista e ritorna True sennò ritorna False
    nodes = [(eNode['addr'], eNode['port']) for eNode in listOfNodes]

    if (node['addr'], node['port']) not in nodes:
        logging.debug('OK:  Adding node {}:{}'.format(node['addr'], node['port']))
        listOfNodes.append(node)
    else:
        logging.debug('NOK: Adding node {}:{}'.format(node['addr'], node['port']))
        return False
    #
    return True

def updateRingLeave(action, listOfNodes):
    logging.debug('RING LEAVE UPDATE')

    # creo dizionario con chiave l'id del nodo e valore il nodo stesso con tutte le sue informazioni per ogni nodo nella lista di nodi
    dictOfNodes = {eNode['id'] : eNode for eNode in listOfNodes}
    
    # Verifica esistenza nodo che vuole rimuoversi nella lista di nodi esistente e se non esiste ritorna False
    if action['id'] not in dictOfNodes:
        logging.debug('NOK: Remove node {}:{}'.format(action['addr'],action['port']))
        return False

    # Prendo il nodo da rimuovere dalla lista di nodi con l'id uguale all'id del nodo che vuole fare leave e lo salvo in nodeToRemove
    nodeToRemove = dictOfNodes[action['id']]

    logging.debug('Removing node {}:{}'.format(nodeToRemove['addr'], nodeToRemove['port']))
    # rimuovo il nodo dalla lista di nodi se l'indirizzo e la porta del nodo da rimuovere sono uguali all'indirizzo e alla porta del nodo nella lista di nodi
    # e ritorno True sennò ritorno False
    if action['addr'] == nodeToRemove['addr'] and action['port'] == nodeToRemove['port']:
        logging.debug('OK:  Remove node {}:{}'.format(action['addr'],action['port']))
        listOfNodes.remove(nodeToRemove)
    else:
        logging.debug('NOK: Remove node {}:{}'.format(action['addr'],action['port']))
        return False
    #
    return True

def updateRing(action, listOfNodes, oracleSocket):
    # può dover compiere una delle seguenti azioni: join, leave
    logging.info('RING UPDATE: {}'.format(action)) # stampa l'azione che deve compiere join o leave e le informazioni del nodo che vuole fare join o leave
    
    try:
        # result è risposta booleana che ottengo quando chiamo una delle due funzioni lambda 
        result = {
            'join'  : lambda param1,param2 : updateRingJoin(param1, param2),
            'leave' : lambda param1,param2 : updateRingLeave(param1, param2)
        }[action['command']](action, listOfNodes)
    except:
        result = False
        return result

    # questa informazione è inviata a tutti i nodi della lista
    sendConfigurationToAll(listOfNodes, oracleSocket)
    
    return result

def sendConfigurationToAll(listOfNodes, oracleSocket):
    # invia la configurazione aggiornata a tutti i nodi della lista ora che è stata aggiornata con il join o il leave di un nodo la lista di nodi
    N = len(listOfNodes)
    # ciclo sulla listofNodes che è stata aggiornata con il join o il leave di un nodo
    # il ciclo con enumerate mi permette di avere l'indice e il nodo stesso nella lista di nodi 
    for idx, node in enumerate(listOfNodes):
        # per ogni nodo devo inviare un messaggio di update al nodo successivo nella lista
        # se idx è uguale a N-1 (ultimo) allora il nodo successivo è il primo della lista altrimenti è il nodo successivo
        if idx == N-1:
            nextNode = listOfNodes[0]
        else:
            nextNode = listOfNodes[idx + 1]
        #logging.debug('UPDATE NODE: ({}) {}:{} --> ({}) {}:{}'.format(\
        #        node['id'],     node['addr'],     node['port'], \
        #        nextNode['id'], nextNode['addr'], nextNode['port']))

        # prendo indirizzo e porta del nodo da contattare
        addr, port = node['addr'], int(node['port'])
        # creo il messaggio da inviare al nodo e metto nel messaggio l'id del nodo e l'id del nodo successivo cosi vede se il suo successivo è cambiato o è rimasto lo stesso
        message = {}
        message['id'] = node['id']
        message['nextNode'] = nextNode
        message = '[CONF] {}'.format(json.dumps(message))
        logging.debug('UPDATE MESSAGE: {}'.format(message))
        # invio il messaggio a ogni nodo dicendogli tu sei il nodo con id id e il tuo successivo è il nodo con id nextNode
        oracleSocket.sendto(message.encode(), (addr, port))
        #

if __name__ == '__main__':

    IP     = argv[1]
    PORT   = int(argv[2])
    bufferSize  = 1024
    listOfNodes = []

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    oracleSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    # l'oracolo deve essere in ascolto su una porta e un indirizzo ip perchè i nodi devono poter comunicare con lui per fare join e leave 
    oracleSocket.bind( (IP, PORT) )

    logging.info("ORACLE UP AND RUNNING!")

    # l'oracolo deve essere in ascolto continuo per ricevere i messaggi dei nodi
    while True:
        # riceve il messaggio e l'indirizzo del mittente che è il nodo che ha inviato il messaggio per fare join o leave
        mess, addr = oracleSocket.recvfrom(bufferSize)
        # decodifica il messaggio ricevuto perchè è in formato byte e lo converte in stringa utf-8
        dmess = mess.decode('utf-8')

        logging.info('REQUEST FROM {}'.format(addr))
        logging.info('REQUEST: {}'.format(dmess))

        # la prima cosa da fare è decodificare il messaggio trasformandolo in comando quindi chiama la funzione decodeMessage
        action = decodeMessage(addr, dmess)
        updateRing(action, listOfNodes, oracleSocket)

        logging.info('UPDATED LIST OF NODES {}'.format(listOfNodes))
