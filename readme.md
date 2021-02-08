# Distributed File Server
### With distributed hash table* election algorithm, distributed files between nodes, and partial file composition
*This represents an early version of the concept and requires further features for use.*  
*This is only for test and practice with distributed servers for education purposes.*  
  
For University Project:  
Christopher Wszolek  
Programmed and tested in python 3.8.5  

This application represents a project done for University class project - the goal of the project was to create a file  
server on a distributed network.  Files would be shared between servers on the this network, and files could be  
split up on these servers (so servers may only contain partial amounts of the file).  

Servers are represented as "nodes", and connection information of each node is maintained by the Distributed Hash Table node (dht).  
The dht is elected by the other nodes, and if it goes offline / isn't responsive, a new dht will be elected.  
Requests to download files are sent to the dht, which returns the information to the requesting node.  If the full file isn't known  
the server information that "may" have the file will be sent (as the download wasn't confirmed to be completed by the source).  

When download occurs, a hash of the file will be sent as well, and when the download is complete the downloader will check the  
has of the file it has downloaded with the hash sent to confirm the full file was sent.

Source code located within:
- node.py
- may_node_list.py
- table.py

Server information must be provided with running program in serverlist.txt.  This is hard-added, but one could imagine an expansion  
that allows a mechanism to add this to the list.

Currently has a timer mechanism to check for download speeds, with curiousity of how running servers in parallel and answering requests in
parallel would affect download rates.

For some further information, please read original readme provided with the project turned in below.

### **ORIGINAL README FOR CLASS**

The dht functionality has been merged into the node file - thus most of the source code is located in node.py.  
__main__ is located within node.py, so this will be the program that will run.  
node.py takes two arguments (argv[]).  argv[1] will determine the ip / port of the server that runs.  
argv[2] will determine the maximum number of nodes that can connect to a DHT.  
To run a single node, in console type "<python directory / command> node.py #<numberofnode> #<maxnumofnodes>  
For example, "python3 Documents/node.py 2 8".  This will run node.py, the third node (0 based), with a max size of 8 nodes.  
Please ensure clientdir0 folder exists with 'test.txt' file within.  
  
For convenience, this will be scripted with pa4deployment file.  
TO RUN DEPLOYMENT SCRIPT, type ./pa4deployment #<maxnumofnodes>.  This will deploy as many nodes automatically,   
creating folders for each that contains the necessary files required. For repeat runs, delete all client# folders  
but client0 folder.  