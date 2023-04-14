#!/usr/bin/python3
import socket
import threading
import logging

HEXAPORT=1214 # it's the Kazaa port! :)

class Listener(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET)
        self.sock.bind(("127.0.0.1",HEXAPORT))
        self.sock.listen(5)
    
    def run(self):
        while True:
            (conn, addr) = self.sock.accept()
            logging.info("Connection from {0}".format(addr))
            #print(conn,addr)

if __name__=="__main__":
    logging.basicConfig(filename="hexa.log",level=logging.INFO)
    l = Listener()
    l.start()
