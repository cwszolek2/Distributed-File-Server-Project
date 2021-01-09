import hashlib
import threading

#helper class - basically helps set up the dht table.
class DHTable():
    class Server():
        def __init__(self, ip, port, operating=True):
            self.ip = ip
            self.port = port
            self.operating = operating
    def __init__(self):
        self.servertable = dict()
    def add_file(self, filename, server):
        #print(filename + ' - ' + str(server.ip) + str(server.port))
        if filename in self.servertable:
            self.servertable[filename].append(server)
        else:
            self.servertable[filename] = [server]
    def remove_file(self, filename, server):
        if filename in self.servertable:
            del self.servertable[filename]
        else:
            print('Error in remove_file: File not found')
