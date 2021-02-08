import hashlib
import logging
import may_node_list
import time
import os
import shutil
import socket
import sys
import table
import threading

from random import random
from threading import Thread

BUF_SIZE = 1024
CLIENT_DIR = ("clientdir" + str(sys.argv[1]))
NUM_OF_PEERS = 0

# Adds 0's up to a packet sent to a socket if it is not == BUF_SIZE
def PAD_MESSAGE(msg):
    msg = msg + ("0" * (BUF_SIZE - (len(msg))))
    return msg

def setup_logger(name, log_file, level=logging.INFO):
    handler = logging.FileHandler(log_file)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

# ClientNode functions both as a normal node, and a dht.  This will carry out most of the 
# normal functions of the node, as well as requests to download.  Server upload commands are
# parsed in innerclass NodeThread
class ClientNode:
    def __init__(self):
        #maybe use port as identifier?  
        self.threads = []
        self.shutdown = False
        self.wait = False
        self.ip = 'localhost'
        self.port = 0
        self.dht = None         # stores dht server information if not this server
        self.nodelist = []      # contains a list of all the other servers ip/port
                                # in format of table.DHTable.Server()
        # dht variables
        self.isdht = False
        self.dhtable = None     # holds file server location information
        self.may_node_table = None
        self.incomplete_file_dict = dict()  # a dictionary of list.  Each list represents an incomplete file
                                            # key = filename
                                            # First item in list will hold total num of chunks, 
                                            # second to end of list will hold num
                                            # of chunks that it has. Key is filename.

    # Starts the server up for the node.
    def start_server(self):
        print('Server Started: ' + self.ip + str(self.port))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.ip, self.port))
        #double check this listen arg
        sock.listen(40)
        return sock

    # Makes a nodelist based on the available server list in serverlist.txt
    def make_node_list(self):
        nodes_file = open('serverlist.txt', 'r')
        for i in range(NUM_OF_PEERS):
            line = nodes_file.readline()
            if not line:
                break
            info = line.split(' ')
            ip = info[0]
            port = info[1]
            #operating = True to begin with
            self.nodelist.append(table.DHTable.Server(ip, port, operating=True))
    
    # Looks for an operating dht server by pinging active servers.
    # If none running, will call start_election() to have one made.
    def find_dht(self):
        msg = 'dht|'
        msg = msg + ("0" * (BUF_SIZE - len(msg)))
        rec_list = []
        for i in range(len(self.nodelist)):
            if self.nodelist[i].port == self.port:
                continue
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            try:
                sock.connect((self.nodelist[i].ip, int(self.nodelist[i].port)))
                checkmsg = sock.recv(BUF_SIZE).decode()
                checkmsg = msg.split('|')[0]
                #Really can't think of what to do with these commands, just leaving them for now
                if checkmsg == 'accept':
                    #print('accept')
                    pass
                elif checkmsg == 'reject':
                    #print('reject')
                    pass
                elif checkmsg == 'not':
                    #print('not')
                    pass
                sock.send(msg.encode())
                rec_msg = sock.recv(BUF_SIZE).decode()
            # server isn't running
            except socket.error:
                self.nodelist[i].operating = False
                continue
            rec_list.append(rec_msg.split('|', 1)[0]) 
        if not rec_list:
            # print(self.port, 'no dht exists')
            # TODO: start DHT election here.
            self.start_election()
        else:
            #print(rec_list)
            ip = rec_list[0].split(' ')[0]
            port = rec_list[0].split(' ')[1]
            self.dht = ip + ' ' + port

    # Finds a server to act as the DHT, and notifies the server of it being the
    # new dht.  If it is the calling server that is dht, it will become the dht.
    def start_election(self, full=False):
        leader = None
        # go through list - see what active servers have the highest port
        for i in range(len(self.nodelist)):
            #check = nodelist[i].ip + ' ' + nodelist[i].port
            if self.nodelist[i].operating == False:
                continue
            
            if self.nodelist[i].port > leader:
                leader = self.nodelist[i]
        self.dht = leader
        if leader == None:
            #dht_logger.info(str(self.port) + "is dht")
            self.become_dht()
        elif leader.port == self.port:
            #dht_logger.info(str(self.port) + "is dht")
            self.become_dht()
        else:
            # if leader is a different node - tell all nodes this is the new dht
            #dht_logger.info(str(self.dht) + "is dht")
            msg = 'new|' + self.dht.split(' ')[0] + '|' + self.dht.split(' ')[1] + '|'
            msg = msg + ("0" + (BUF_SIZE - len(msg)))
            for i in range(len(self.nodelist)):
                if(self.nodelist[i].operating == False):
                    continue
                else:
                    sock = socket.socket(sock.AF_INET, socket.SOCK_STREAM)
                    sock.connect((self.nodelist[i].ip, self.nodelist[i].port))
                    sock.send(msg.encode())
    # Calling node becomes the acting dht.
    def become_dht(self):
        if self.isdht != True:
            self.isdht = True
            self.dht = self.ip + ' ' + str(self.port)
            print('TEST: ' + self.ip + str(self.port) + 'IS DHT')
        else:
            print('already dht')
        #TODO: if there are any more requirements, do it here

    # Connects to dht
    def dht_connect(self):
        if self.isdht == True:
            return False   
        dht_ip = self.dht.split(' ')[0]
        dht_port = int(self.dht.split(' ')[1])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((dht_ip, dht_port))
        msg = sock.recv(BUF_SIZE).decode()
        msg = msg.split('|')[0]
        if msg == 'reject':
            self.start_election()
        
        return sock

    # Sends the files contained by the node's directory to the acting dht.  If the dht
    # is self, just stores that information it has on its own.
    def send_file_directory(self):
        if self.isdht == True:
            current_files = (os.listdir(CLIENT_DIR))
            ip_port = self.ip + ':' + str(self.port)
            server = table.DHTable.Server(self.ip, self.port)
            for i in range(len(current_files)):
                # Not sure self.dhtable will work - double check
                self.dhtable.add_file(current_files[i], server)
        else:
            current_files = (os.listdir(CLIENT_DIR))
            current_files = ','.join(current_files)
            ip_port = self.ip + ':' + str(self.port)
            file_list_sent = 'list|' + ip_port + '|' + current_files + '|'
            file_list_sent = file_list_sent + ("0" * (BUF_SIZE - len(file_list_sent)))
            dht_sock = self.dht_connect()
            dht_sock.send(file_list_sent.encode())
            dht_sock.close()        
    
    #TODO def send_handshake(self, filename, socket, )
    # get handshake should be in server thread
    #TODO def get_handshake(self, socket)

    # Gets the location of the server holding the file from the dht.  Then it will
    # download the file from that server.  If the dht is self, then will just
    # get the information of the server from itself, and then downloda the file from
    # the server.  Logs download time into log file.
    def download_file(self, file_name):
        #If the node is a dht, no need to connect to dht to get ip/port
        #download algorithm is the same - consider moving to helper method if time allows

        #NOTE - if this doesn't work, rollback to PA3 version.
        download_ip = None
        download_port = None
        may = None
        file_chunks = 0
        start_chunk = 0 # Starting chunk of download
        end_chunk = 0 # Ending chunk of download
        full_file = 1 # Server has full file
        
        # This makes the assumption that downloads will only be missing from 
        # the end of a section to the end of the file, and no "holes" in the file
        if 'file_name' in self.incomplete_file_dict:
            # TODO-potential bug here if [-1] == [0] because that means there is no
            # data in this file as it failed on the first chunk transaction.
            start_chunk = self.incomplete_file_dict.get(file_name)[-1]

        if self.isdht == True:
            servers = None 
            for i in range(len(self.dhtable.servertable.get(file_name))):
                if(self.dhtable.servertable.get(file_name)[i].operating is True):
                    servers = self.dhtable.servertable.get(file_name)[i]
                    break
            if servers == None:
                for i in range(len(self.may_node_table.may_exist_table.get(file_name))):
                    if (self.may_node_table.may_exist_table.get(file_name)[i].operating is True):
                        servers = self.may_node_table.may_exist_table.get(file_name)[i]
                        break
            self.may_node_table.add_may_file(file_name, servers)
            download_ip = servers.ip
            download_port = servers.port
        # Not DHT - need to connect to DHT to get server IP / PORT to download
        # from.
        else:
            download_request = 'getf|' + file_name + '|' + self.ip + '|' + str(self.port) + '|'
            download_request = PAD_MESSAGE(download_request)
            dht_sock = self.dht_connect()
            dht_sock.send(download_request.encode())
            server_info = str(dht_sock.recv(BUF_SIZE).decode())
            # dht replied that server is in the may_node_list
            if 'may' in server_info:
                may = 1
            dht_sock.close()
            server_info = server_info.split('|', 1)[0]
            if(server_info[0] == 'notfound'):
                print('Error in download file: file not found in distributed hash table')
            server_info = server_info.split(':', 1)
            #print('server_info downloading from: ', server_info)
            # Connect to actual node that has file and download file
            download_ip = server_info[0]
            download_port = int(server_info[1])

        download_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        download_sock.connect((download_ip, download_port))
        cmsg = download_sock.recv(BUF_SIZE).decode()
        if may == 1:
            # TODO - should move this into its own method
            handshake_message = 'handshake|' + file_name + '|' + str(start_chunk) + '|'
            handshake_message = PAD_MESSAGE(handshake_message)
            download_sock.send(handshake_message.encode())
            handshake_recv = download_sock.recv(BUF_SIZE).decode()
            their_chunks = int(handshake_recv.split('|', 1)[1])
            if their_chunks > start_chunk:
                end_chunk = their_chunks
            if their_chunks != 0:
                full_file = 0 # Server does not have full file
        node_download_request = 'download|' + file_name + '|' + str(start_chunk) + '|' + str(end_chunk) + '|'
        node_download_request = PAD_MESSAGE(node_download_request)
        download_sock.send(node_download_request.encode())
        # Getting file size and file hash information
        download_size = download_sock.recv(BUF_SIZE).decode()
        download_size = int(download_size.split('|')[0])
        download_size = int(download_size)
        file_hash = download_sock.recv(BUF_SIZE).decode()
        file_hash = file_hash.split('|')[0]
        if full_file == 1 and file_name not in self.incomplete_file_dict:
            num_of_chunks = download_size / BUF_SIZE
            self.incomplete_file_dict[file_name] = [num_of_chunks]
        received = 0
        start_time = time.perf_counter()
        # Starting download
        with open(CLIENT_DIR + '/' + file_name, 'w+b') as f:
            f.seek(int(start_chunk) * BUF_SIZE)
            num_of_chunk = int(start_chunk)
            while received < download_size:
                num_of_chunk = num_of_chunks + 1
                data = download_sock.recv(min(download_size - received, BUF_SIZE))
                if not data:
                    break
                f.write(data)
                received = received + len(data)
                self.incomplete_file_dict.get(file_name).append(num_of_chunk)
            f.seek(0)
            recvd_hash = hashlib.md5(f.read()).hexdigest()
            if recvd_hash != file_hash:
                print('ERROR: File hash does not match')
            else:
                print('File hash matches')
            # whole file was downloaded - can remove from incomplete file dict
            if full_file == 1:
                del self.incomplete_file_dict[file_name]
            f.close()
        end_time = time.perf_counter()
        total_time = end_time - start_time
        client_logger.info(str(total_time) + ',' + str(download_ip) + str(download_port))
        
    # Closes the actively running server.
    # TODO: this doesn't work still.
    def close_server(self, server_sock):
        #not sure if i need to send IP and port information too
        close_request = 'close|' + ("0" * (BUF_SIZE - len('close|')))
        dht_sock = self.dht_connect()
        dht_sock.send(close_request.encode())
        dht_sock.close()
        print('Shuting down server')
        server_sock.close()
        exit()

    # This is the primary method to start running the node, both server
    # and client side.  Will ask users for commands to run / download
    def start_node(self, port):
        self.port = port
        self.make_node_list()
        self.find_dht()
        if (self.isdht == True) and (not self.dhtable):
            self.dhtable = table.DHTable()
            self.may_node_table = may_node_list.MayNodeTable()
        self.send_file_directory()
        server_sock = self.start_server()
        # Starts the server thread for accepting requests from other servers
        server_thr = node.ServerThread(self.ip, self.port, server_sock, self.dht, 
                                        self, self.isdht, self.dhtable, may_node_table=self.may_node_table)
        server_thr.start()
        # Primary running loop for the client - used to download files from other servers
        while not self.shutdown:
            try:
                #TODO: check if this works
                if self.isdht == True and not self.dhtable:
                    self.dhtable = table.DHTable()
                    self.may_node_table = may_node_list.MayNodeTable()
                if self.wait is False:
                    print('Command List:\n\tdownload <filename>\n\twait (press ctrl + c to stop waiting)\n\tstop (closes node)')
                    userinput = None
                    try: 
                        userinput = input('Enter command:')     
                    except:
                        if userinput == None:
                            pass
                    if 'download' in userinput:
                        userinput = userinput.replace('download ','')
                        print(userinput)
                        self.download_file(userinput)
                        # updating the server post-download
                        self.send_file_directory()
                        continue
                    elif userinput == 'wait':
                        print('wait\nWait IP/Port: ', self.ip, str(self.port))
                        self.wait = True
                        print('Press ctrl + c to stop waiting')
                    elif userinput == 'stop':
                        self.shutdown = True
                        self.close_server(server_sock)
                        break
                    else:
                        print('Error: invalid command')
                    continue
            
            # Can press ctrl + c to interrupt the waiting loop
            except KeyboardInterrupt:
                self.wait = False
                
        # While loop ended
        # Cleaning up and closing
        for t in self.threads:
            t.join()
        server_sock.close()
    
    # Primary thread used to look for requests from other servers.  If found, will call a 
    # NodeThread to handle the request.
    class ServerThread(Thread):
        def __init__(self, ip, port, sock, dht, client_node, isdht, dhtable, may_node_table=None):
            Thread.__init__(self)
            self.ip = ip
            self.port = port
            self.sock = sock
            self.dht = dht
            self.threads = []
            self.node = client_node
            self.isdht = isdht
            self.dhtable = dhtable
            self.may_node_table = may_node_table
        def run(self):
            while True:
                # TODO: think about this more and implement server thread better
                (clientsock, (clientip, clientport)) = self.sock.accept()
                if self.isdht == True:
                    if self.check_thread_count(clientsock) is False:
                        continue
                else:
                    msg = 'not|'
                    msg = PAD_MESSAGE(msg)
                    clientsock.send(msg.encode())
                newthread = ClientNode.NodeThread(clientip, clientport, clientsock, 
                                                  self.dht, self.node, self.isdht, 
                                                  self.dhtable, may_node_table=self.may_node_table)
                newthread.start()
            for t in self.threads:
                t.join()
        def check_thread_count(self, sock):
            if len(self.threads) > NUM_OF_PEERS:
                msg = 'reject|'
                msg = PAD_MESSAGE(msg)
                sock.send(msg.encode())
                return False
            else:
                msg = 'accept|'
                msg = PAD_MESSAGE(msg)
                sock.send(msg.encode())
                return True
    
    # Thread used by the ServerThread to handle requests from other nodes.  Interprets and handles commands
    # from other nodes.  
    class NodeThread(Thread):
        def __init__(self, ip, port, sock, dht, client_node, isdht, dhtable, may_node_table=None):
            Thread.__init__(self)
            self.ip = ip
            self.port = port
            self.sock = sock
            self.dht = dht
            self.node = client_node
            self.isdht = isdht
            self.dhtable = dhtable
            self.may_node_table = may_node_table
        def run(self):
            try:
                msg = self.sock.recv(BUF_SIZE).decode()
            except:
                pass
            self.get_command(msg)
            self.sock.close()

        # Parser used to read messages from other servers.
        def get_command(self, command_string):
            command = command_string.split('|', 1)[0]
            msg_list = command_string.split('|', 1)
            # request to find out who the current dht is.  If none, will timeout.
            if command == 'dht':
                if self.dht != None:
                    msg = PAD_MESSAGE(self.dht + '|')
                    self.sock.send(msg.encode())
                    self.sock.close()
            # message sent to inform other servers who the new dht is after an election.
            elif command == 'new':
                msg_list = msg_list[1].split('|')
                self.dht = msg_list[0] + msg_list[1]
                if self.port == msg_list[1]:
                    # TODO: figure out how to handle this becoming dht
                    self.node.become_dht()
                else:
                    #connect to dht and send file list
                    self.node.send_file_directory()
            # Request to download a file from this server.
            elif command  == 'download':
                download_request = msg_list[1].split('|')[0]
                start_chunk = msg_list[1].split('|')[1]
                end_chunk = msg_list[1].split('|')[2]
                current_files = (os.listdir(CLIENT_DIR))
                if download_request not in current_files and download_request not in self.node.incomplete_file_dict:
                    print('ERROR: in node NodeThread: file not found for p2p download request')
                else:
                    f = open(CLIENT_DIR + '/' + download_request, 'rb')
                    file_size = self.send_file_size(download_request, start_chunk)
                    self.send_file_hash(download_request, f)
                    f.seek(int(start_chunk) * BUF_SIZE)
                    upload_start = time.perf_counter()
                    self.send_file(f, file_size)
                    upload_end = time.perf_counter()
                    upload_time = upload_end - upload_start
                    server_logger.info(str(upload_time))
                    f.close()
                    self.sock.close()
            elif command == 'handshake':
                own_chunks = 0

                file_name = msg_list[1].split('|')[0]
                their_chunks = msg_list[1].split('|')[1]
                # own_chunks = 0 means full file is there.
                if(file_name in current_files):
                    own_chunks = 0
                elif(file_name in self.node.incomplete_file_dict):
                    own_chunks = self.node.incomplete_file_dict.get(file_name)[-1]
                else:
                    own_chunks = -1
                return_handshake_msg = 'rehshake' + '|' + str(own_chunks) + '|'
                return_handshake_msg = PAD_MESSAGE(return_handshake_msg)
                self.sock.send(return_handshake_msg.encode())
                # Don't close sock because we want to keep it open for download
            # Specific commands only for dht
            elif self.isdht == True:
                # Informs the dht of the current files of the sending server
                if command == 'list':
                    other_string = command_string.split('|', 1)[1]
                    ip_port = command_string.split('|')[1]
                    #print('ip_port: ', ip_port)
                    client_ip = ip_port.split(':')[0]
                    client_port = ip_port.split(':')[1]
                    file_list = other_string.split('|', 2)[1]
                    file_list = file_list.split(',')
                    # TO DO double check this syntax
                    server = table.DHTable.Server(client_ip, client_port, True)
                    for i in range(len(file_list)):
                        # Not sure self.dhtable will work - double check
                        self.dhtable.add_file(file_list[i], server)
                # Request to get the IP/PORT of a server having the given file
                elif command == 'getf':
                    found = 0
                    other_string = command_string.split('|')[1]
                    interested_ip = command_string.split('|')[2]
                    interested_port = command_string.split('|')[3]
                    for i in reversed(range(len(self.dhtable.servertable.get(other_string)))):
                        if(self.dhtable.servertable.get(other_string)[i].operating is True):
                            servers = self.dhtable.servertable.get(other_string)[i]
                            servers = str(servers.ip) + ':' + str(servers.port) + '|'
                            servers = PAD_MESSAGE(servers)
                            self.sock.send(servers.encode())
                            found = 1
                            interested_server = table.DHTable.Server(interested_ip, interested_port)
                            self.may_node_table.add_may_file(other_string, interested_server)
                            break
                    if found == 0:
                        # Not found in file list, check may_node_table and send server info if found
                        for i in range(len(self.may_node_table.may_exist_table.get(other_string))):
                            if(self.may_node_table.may_exist_table.get(other_string)[i].operating is True):
                                servers = self.may_node_table.get(other_string)[i]
                                servers = 'may' + '|' + str(servers.ip) + ':' + str(servers.port) + '|'
                                servers = PAD_MESSAGE(servers)
                                self.sock.send(servers.encode())
                                found = 1
                                interested_server = table.DHTable.Server(interested_ip, interested_port)
                                self.may_node_table.add_may_file(other_string, interested_server)
                                break
                        if found == 0:
                            not_found = 'notfound|' + ("0" * (BUF_SIZE - len('notfound')))
                            self.sock.send(not_found).encode()
                # Informing the DHT about a server shutting down - changing the server to operating = False
                elif command == 'close':
                    # TODO - fix this.  Not working, not crazy hard but time consuming
                    for i in self.dhtable.servertable:
                        for j in self.dhtable.servertable[i]:
                            if self.ip == self.dhtable.servertable[i][j].ip and self.port == self.dhtable.servertable[i][j].port:
                                self.dhtable.servertable[i][j].operating = False

        # TODO - make this into chunk sized file bits.
        def send_file_size(self, filename, start_chunk):
            file_dir = CLIENT_DIR + '/' + str(filename)
            file_size = str(os.path.getsize(file_dir))
            size_had_before = start_chunk * BUF_SIZE
            file_size = int(file_size) - int(size_had_before)
            file_size_padded = str(file_size) + '|'
            file_size_padded = file_size_padded + ("0" * (BUF_SIZE - len(file_size_padded)))
            self.sock.send(file_size_padded.encode())
            return file_size
        
        def send_file_hash(self, filename, filepointer):
            file_hash = hashlib.md5(filepointer.read()).hexdigest()
            filepointer.seek(0)
            file_hash = file_hash + '|'
            file_hash = file_hash + ("0" * (BUF_SIZE - len(file_hash)))
            self.sock.send(file_hash.encode())
        
        def send_file(self, filepointer, filesize):
            total_size = 0
            while total_size < int(filesize):
                data = filepointer.read(BUF_SIZE)
                if not data:
                    break
                sent = self.sock.send(data)
                total_size += sent


if __name__ == "__main__":    
    if sys.argv[1] is None:
        print('Error: please enter client number as argument')
        exit(0)
    entered_arg = int(sys.argv[1])
    total_arg = int(sys.argv[2])
    port = 5000 + (100 * entered_arg)
    if entered_arg == None:
        print('Argv entered: ',entered_arg)
        print('Error: please enter number size greater than argv[1]')
        exit(0)
    if not os.path.exists(CLIENT_DIR):
        os.makedirs(CLIENT_DIR)
    shutil.copy('serverlist.txt', CLIENT_DIR)
    client_logger = setup_logger('client_logger', 'client_logfile.log')
    server_logger = setup_logger('server_logger', 'server_logfile.log')
    node_logger = setup_logger('timestep_logger', 'timestep_logfile.log')
    NUM_OF_PEERS = int(sys.argv[2])
    node = ClientNode()
    node.start_node(port)
