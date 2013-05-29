#!/usr/bin/python
# --encoding:utf-8--

import sys
import threading
import Queue
import gevent
from gevent import pool

lock = threading.Lock()
t_queue = Queue.Queue()

class GTimer(threading.Thread):
    def __init__(self):
        super(GTimer, self).__init__()
        p = pool.Pool()
    
    def run(self):
        item = t_queue.get()
        
        flag = True