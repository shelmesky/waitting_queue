#!/usr/bin/python
# --encoding:utf-8--

import threading
import time


cond = threading.Condition()

vm_list = [0,1,2,3,4,5,6,7,8,9]

class t1(threading.Thread):
    def __init__(self):
        super(t1, self).__init__()
    
    def run(self):
        if cond.acquire():
            while 1:
                if len(vm_list) < 10:
                    print vm_list
                cond.wait()
                print "t1: receive notify"


class t2(threading.Thread):
    def __init__(self):
        super(t2, self).__init__()
    
    def run(self):
        if cond.acquire():
            vm_list.pop()
            vm_list.pop()
            # notify只是释放了内部的锁，外部的RLock需要wai释放或者release释放
            # wait的一开始有_release_save就是释放了外部的锁
            cond.notify()
            print "t2: notify has sent"
            time.sleep(2)
            cond.release()


class t3(threading.Thread):
    def __init__(self):
        super(t3, self).__init__()
    
    def run(self):
        if cond.acquire():
            vm_list.pop()
            vm_list.pop()
            cond.notify()
            print "t3: notify has sent"
            time.sleep(2)
            cond.release()


if __name__ == '__main__':
    T1 = t1()
    T2 = t2()
    T3 = t3()
    
    T1.start()
    T2.start()
    T3.start()

