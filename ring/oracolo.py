import socket
from sys import argv
import logging
import re
import json

def decodeJoin(addr, mess):
    # Va a cercare la presenza di un json nel messaggio
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\, ]*\})' , mess)
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))
        action = json.loads(result.group(1))
    else:
        action = {}
    
    action['command'] = 'join'

    return action

def decodeLeave(addr, mess):
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\, ]*\})' , mess)
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))
        action = json.loads(result.group(1))
    else:
        action = {}
    
    action['command'] = 'leave'
    
    return action

def decodeMessage(addr, mess):
    result = re.search('^\[([A-Z]*)\]' , mess)
    if bool(result):
        command = result.group(1)
        logging.debug('COMMAND: {}'.format(command))

        try:
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
    node = {}

    id_ = 1
    idList = [int(eNode['id']) for eNode in listOfNodes]
    for i in range(1, len(listOfNodes)+2):
        if i not in idList:
            id_ = i
            break
    
    node['id']   = str(id_)
    node['port'] = action['port']
    node['addr'] = action['addr']

    # Verifica esistenza nodo nella lista di nodi
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

    # creo dizionario con chiave id e valore nodo
    dictOfNodes = {eNode['id'] : eNode for eNode in listOfNodes}
    
    if action['id'] not in dictOfNodes:
        logging.debug('NOK: Remove node {}:{}'.format(action['addr'],action['port']))
        return False

    nodeToRemove = dictOfNodes[action['id']]

    logging.debug('Removing node {}:{}'.format(nodeToRemove['addr'], nodeToRemove['port']))
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
    logging.info('RING UPDATE: {}'.format(action))
    
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
    N = len(listOfNodes)
    # ciclo sulla listofNodes che è stata aggiornata con il join o il leave di un nodo 
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
        oracleSocket.sendto(message.encode(), (addr, port))
        #

if __name__ == '__main__':

    IP     = argv[1]
    PORT   = int(argv[2])
    bufferSize  = 1024
    listOfNodes = []

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    oracleSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    oracleSocket.bind( (IP, PORT) )

    logging.info("ORACLE UP AND RUNNING!")

    while True:
        mess, addr = oracleSocket.recvfrom(bufferSize)
        dmess = mess.decode('utf-8')

        logging.info('REQUEST FROM {}'.format(addr))
        logging.info('REQUEST: {}'.format(dmess))

        # la prima cosa da fare è decodificare il messaggio quindi chiama la funzione decodeMessage
        action = decodeMessage(addr, dmess)
        updateRing(action, listOfNodes, oracleSocket)

        logging.info('UPDATED LIST OF NODES {}'.format(listOfNodes))
