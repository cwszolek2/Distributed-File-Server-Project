For University Project:
Christopher Wszolek
Programmed and tested in python 3.8.5

README

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

