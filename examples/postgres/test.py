#!/usr/bin/env python3

import multiprocessing
import os
import subprocess
import time

host = 'localhost'
port = '5432'
user = 'postgres'
dbname = 'postgres'
password = os.environ['POSTGRES_PASSWORD']
with open(os.path.join(os.environ['HOME'], '.pgpass'), 'w') as pgpass:
    pgpass.write(':'.join([host,port,user,dbname,password]))

server = multiprocessing.Process(target=subprocess.run, kwargs={ 'args' : ['/docker-entrypoint.sh', 'postgres'] })
server.start()
time.sleep(15)

client = multiprocessing.Process(target=subprocess.run, kwargs={ 'args' : ['psql', '-h', host, '-p', port, '-U', user, dbname, '-f', 'test.sql', '-e', '-q', '-A', '-t'] })
client.start()
client.join()

server.terminate()
