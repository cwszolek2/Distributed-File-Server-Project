import hashlib
import threading
from table import DHTable

#Could use inheritance here, but I feel like having the same variable names makes things confusing
class MayNodeTable():
    def __init__(self):
        self.may_exist_table = dict()
    def add_may_file(self, filename, server):
        if filename in self.may_exist_table:
            self.may_exist_table[filename].append(server)
        else:
            self.may_exist_table[filename] = [server]
    
    # TODO - code this            
    #def remove_server(self, filename, server):
    #    if filename in self.may_exist_table:

    # This seems wrong - maybe change this?
    def remove_may_file(self, filename, server):
        if filename in self.may_exist_table:
            del self.may_exist_table[filename]
        else:
            print('Error in remove_file: File not found')