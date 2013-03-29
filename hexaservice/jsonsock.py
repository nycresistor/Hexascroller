import socket
import json
import threading

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
            print(conn,addr)

if __name__=="__main__":
    l = Listener()
    l.start()
