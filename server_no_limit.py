#!/usr/bin/python
# --encoding:utf-8--

import os
import sys
import simplejson as json
import threading
import time
import Queue
import pdb
from prettyprint.prettyprint import pp
import copy

from common.server_init import server_init

project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

server_init()

from tornado.options import options

import tornado.ioloop
from tornado import web
from tornado import ioloop
from tornado.web import asynchronous

from common.openstack import nova as nova_api
from common.utils import from_now_to_datetime
from common.utils import cal_seconds_to

from common.mongo_api import running_t_instance as running_t
from common.mongo_api import waitting_t_instance as waitting_t
from common.mongo_api import instance_backup as backup_t

from common.backend.receiver import add_callback

from common.backend.multicast_api import update_nginx_host
from common.backend.multicast_api import add_nginx_host
from common.backend.multicast_api import del_nginx_host

from common.logger import LOG


running_list = list()
timer_list = list()
waitting_queue = Queue.Queue(maxsize=options.waitting_queue_size)
cond = threading.Condition()
seconds = options.instance_survive_times


def rebuild_timer_and_queue():
    '''
    服务器重启时，从mongodb中读取记录并恢复定时器和队列
    启动固定数量的timer
    并将等待的请求放入到等待队列中
    '''
    LOG.info("Rebuild timer and waitting queue")
    running_timer = running_t.query()
    waitters = waitting_t.query()
    for line in running_timer:
        if line.has_key("instance_data"):
            expired_time = line['expired_time']
            seconds = cal_seconds_to(expired_time)
            uuid = line['uuid']
            user_id = line['user_id']
            instance_data = line['instance_data']
            _oid = line['_id']
            # 定时器已经到期，立即删除运行的实例
            if seconds < 0:
                try:
                    nova_api.delete_vm(uuid)
                except:
                    pass
                running_t.delete(uuid=uuid)
                
                # 更新backup_t中的deleted_time
                deleted_time = time.time()
                backup_t.update(dict(uuid=uuid), deleted_time=deleted_time)
            else:
                # 恢复running_dict和定时器
                item = dict(user_id=user_id, instance_data=instance_data)
                item['uuid'] = uuid
                # 2013/03/01
                # 增加_oid到元素，RunningPutter可以根据此_oid删除waitting_t中的元素
                # 其实从mongodb中取得的记录已包含_id
                # 此处为了加强重点，重复加入
                item['_oid'] = _oid
                insert_vm_in_mem(item)
                timer = Timer(uuid=uuid, seconds=seconds, item=item)
                timer.start()
                timer_list.append(timer)
    for line in waitters:
        if line.has_key("instance_data"):
            LOG.info("insert data to waitting queue: %s" % line)
            user_id = line['user_id']
            item = dict(_oid=line['_id'], user_id=user_id,
                        instance_data=instance_data)
            waitting_queue.put(item)
    LOG.info("Rebuild end")


def del_vm_in_mem(uuid):
    for item in running_list:
        if item['uuid'] == uuid:
            running_list.remove(item)
            return


def insert_vm_in_mem(item):
    running_list.append(item)


def check_max_instance_for_user(user_id):
    count = 1
    for item in running_list:
        if item['user_id'] == user_id:
            count += 1
    LOG.info("instances for %s is %s" % (user_id, count))
    return count


def process_request(user_id, instance_data):
    '''
    处理用户的请求
    如果运行队列未满，则创建虚拟机实例、启动定时器、在running_t中插入记录
    否则将请求投入排队的队列中，并在waitting_t中插入记录
    '''
    item = dict(user_id=user_id, instance_data=instance_data)
    os = instance_data['os']
    
    # 如果运行队列未满
    if len(running_list) < options.running_dict_size:
        # 创建实例
        uuid = nova_api.create_vm(item)
        item['uuid'] = uuid
        
        # 为实例增加端口映射
        balancer = addNginxHost(uuid, os)
        balancer.start()
        
        # 实例加入到running_dict中
        insert_vm_in_mem(item)
        
        # 实例的到期时间
        expired_time = from_now_to_datetime(seconds=seconds)
        
        # 启动定时器
        timer = Timer(uuid=uuid, item=item,
                      seconds=cal_seconds_to(expired_time))
        timer.start()
        timer_list.append(timer)
        
        # 在running_t中插入一条记录
        obj_id = running_t.insert(uuid=uuid, user_id=user_id,
                         expired_time=expired_time, instance_data=instance_data)
        
        # 请求被立即处理
        # 日志表里插入created_time和processed_time
        # 并增加running_id，用于删除实例时更新deleted_time
        # user_id用于查询用
        processed_time = time.time()
        backup_t.insert(user_id=user_id, created_time=processed_time, processed_time=processed_time,
                        instance_data=instance_data, running_id=obj_id, uuid=uuid)
        LOG.info("Start timer for {0}: {1}".format(user_id, instance_data))
        # 返回0
        return 0
    else:
        # 创建时间
        created_time = from_now_to_datetime()
        item.setdefault("created_time", created_time)
        
        # 在waitting_t中加入请求
        obj_id = waitting_t.insert(**item)
        
        # 请求被排队
        # 日志表里插入created_time，并增加waitting_id
        # waitting_id是在waitting_t中获得的id
        # 用于在RunningPutter线程中更新processed_time
        # NOTICE: 目前使用uuid作为删除实例时更新deleted_time的条件
        # user_id用于查询
        created_time = time.time()
        backup_t.insert(user_id=user_id, created_time=created_time, waitting_id=obj_id,
                        instance_data=instance_data)
        
        # 将请求加入到等待队列
        # 2013/02/20: 将db的_objectid也压入队列
        # 在waitting_t中删除元素的时候，就根据_objectid删除
        # 而不是user_id
        item['_oid'] = obj_id
        waitting_queue.put(item)
        
        LOG.info("put data to waitting queue {0}: {1}".format(user_id, instance_data))
        result = waitting_t.query(_id=obj_id)
        
        # 返回排队的序号
        for line in result:
            return line['auto_id']


class addNginxHost(threading.Thread):
    '''
    为每个实例调用NGINX负载均衡
    增加一个端口映射到管理端口
    '''
    def __init__(self, uuid, os):
        super(addNginxHost, self).__init__()
        self.uuid = uuid
        self.os = os
    
    def run(self):
        while 1:
            try:
                ip_addr = nova_api.query_vm(self.uuid)
            except Exception, e:
                LOG.exception(e)
                return
            if ip_addr:
                break
            time.sleep(1)
        if self.os == "linux":
            add_nginx_host(self.uuid, ip_addr, 22)
        if self.os == "windows":
            add_nginx_host(self.uuid, ip_addr, 3389)
        return


class RunningPutter(threading.Thread):
    '''
    线程启动时，排队的队列是空的，进入等待状态
    定时器线程到时间后，会通知此线程，说明等待的条件达到了
    '''
    def __init__(self):
        super(RunningPutter, self).__init__()
        self.run_count = 0
    
    def run(self):
        if cond.acquire():
            while 1:
                if len(running_list) < options.running_dict_size \
                and not waitting_queue.empty():
                    
                    # 从等待队列中获取元素
                    item = waitting_queue.get()
                    
                    try:
                        # 创建实例
                        uuid = nova_api.create_vm(item)
                        item['uuid'] = uuid
                    except Exception, e:
                        waitting_t.delete(_id=item['_oid'])
                    else:
                    
                        # 为实例增加端口映射
                        os = item['instance_data']['os']
                        balancer = addNginxHost(uuid, os)
                        balancer.start()
                        
                        # 实例加入到running_dict中
                        insert_vm_in_mem(item)
                        
                        # 实例的到期时间            
                        expired_time = from_now_to_datetime(seconds=seconds)
                        # 启动定时器
                        timer = Timer(uuid=uuid, item=item,
                                      seconds=cal_seconds_to(expired_time))
                        timer.start()
                        timer_list.append(timer)
                        
                        # 在running_t中插入记录
                        obj_id = running_t.insert(uuid=uuid, user_id=item['user_id'],
                                         expired_time=expired_time,
                                         instance_data=item['instance_data'])
                        
                        # 从等待的waitting_t中删除对应的记录
                        # 2013/02/20: 根据_id删除，而不是user_id
                        waitting_t.delete(_id=item['_oid'])
                        LOG.info("Get item from waitting_queue: %s" % item)
                        
                        # 排队的请求被处理，根据waitting_id更新processed_time
                        # 并增加running_id，用于删除时例时更新deleted_time
                        # NOTICE: 目前使用uuid更新backup_t中deleted_time的条件
                        processed_time = time.time()
                        backup_t.update(dict(waitting_id=item['_oid']),
                                        processed_time=processed_time,
                                        uuid=uuid, running_id=obj_id)
                else:
                    cond.wait()


class Timer(threading.Thread):
    '''
    定时器线程
    '''
    def __init__(self, uuid=None, item=None, seconds=None):
        super(Timer, self).__init__()
        self.uuid = uuid
        self.seconds = float(seconds)
        LOG.info("Timer remain:  %s" % self.seconds)
        LOG.info("Start timer at: %s" % from_now_to_datetime())
    
    def run(self):
        '''
        暂停指定的时间，到时间后执行一些列动作
        '''
        time.sleep(self.seconds)
        result = running_t.query_one(uuid=self.uuid)
        if result:
            if cond.acquire():
                # 从running_dict中删除用户
                try:
                    del_vm_in_mem(self.uuid)
                    # nginx负载均衡中删除主机
                    del_nginx_host(self.uuid)
                except Exception, e:
                    LOG.exception(e)
                # 从running_t中删除用户
                running_t.delete(uuid=self.uuid)
                # 调用openstack删除主机
                nova_api.delete_vm(self.uuid)
                
                # 更新backup_t中的deleted_time
                deleted_time = time.time()
                backup_t.update(dict(uuid=self.uuid), deleted_time=deleted_time)
                
                # 通知排队线程
                cond.notify()
                cond.release()
                return


class Deleter(threading.Thread):
    def __init__(self, uuid=None, obj=None):
        super(Deleter, self).__init__()
        self.uuid = uuid
        self.obj = obj
    
    def run(self):
        if cond.acquire():
            del_vm_in_mem(self.uuid)
            # 当调用cloudopen接口处理失败时，调用tornado返回404
            try:
                del_nginx_host(self.uuid)
                nova_api.delete_vm(self.uuid)
            except Exception, e:
                LOG.exception(e)
                self.obj.send_error(500)
            running_t.delete(uuid=self.uuid)
            
            # 更新backup_t中的deleted_time
            deleted_time = time.time()
            backup_t.update(dict(uuid=self.uuid), deleted_time=deleted_time)
            
            # 当全部处理成功后，调用tornado返回成功状态
            self.obj.write({"status": 0})
            tornado.ioloop.IOLoop.instance().add_callback(self.obj.on_write)
            
            cond.notify()
            cond.release()
            return


class iApplication(web.Application):
    '''
    URL路由
    '''
    def __init__(self):
        handlers = [
            (r"/api", MainHandler),
            (r"/api/uuid", UUIDHandler),
            (r"/api/system", SystemHandler),
            (r"/api/user", UserHandler),
            (r"/api/status", StatusHandler),
        ]
        
        web.Application.__init__(self, handlers)


class MainHandler(web.RequestHandler):
    def get(self):
        '''
        根据用户id返回用户排队的序号
        找不到则返回-1
        '''
        return_list = list()
        user_id = self.get_argument("user_id")
        result = waitting_t.query(user_id=user_id)
        
        # 用户正在排队的位置 = 排队位置 - 被删除的
        # 被删除的 = 计数器 - 正在等待的
        auto_id = waitting_t.get_auto_incre() - 1
        waitting = waitting_t.count() - 1
        deleted = auto_id - waitting
        for line in result:
            temp = dict()
            #temp['request_id'] = line['_id']
            temp['position'] = line['auto_id'] - deleted
            return_list.append(temp)
        if not return_list:
            self.write(dict(status=[]))
            return
        self.write(dict(status=return_list))
        return

    def post(self):
        '''
        接收用户的请求
        如果可以立即处理则返回0，否则需要排队则返回排队序号
        如果同一个用户重复请求则返回-1
        '''
        user_id = self.get_argument("user_id")
        server_os = self.get_argument("os")
        server_name = self.get_argument("name")
        instance_data = dict(os=server_os, name=server_name)
        
        if check_max_instance_for_user(user_id) <= 2:
            auto_id = process_request(user_id, instance_data)
            if auto_id == 0:
                self.write(dict(status = 0))
            else:
                self.write(dict(status = auto_id))
        else:
            self.write({"status": -1})
    
    @asynchronous
    def delete(self):
        uuid = self.get_argument("uuid")
        result = running_t.query_one(uuid=uuid)
        if result:
            deleter = Deleter(uuid=uuid, obj=self)
            deleter.start()
        else:
            self.send_error(404)
    
    def on_write(self):
        self.finish()
    


class UUIDHandler(web.RequestHandler):
    def get(self):
        uuid = self.get_argument("uuid")
        result = running_t.query_one(uuid=uuid)
        try:
            os = result['instance_data']['os']
            host = result['host']
            port = result['port']
            self.write({"status": {"uuid": uuid, "host": host,
                                   "port": port, "os": os}})
        except:
            self.send_error(404)


class SystemHandler(web.RequestHandler):
    def get(self):
        max_queue_size = options.running_dict_size
        running_size = len(running_list)
        available = max_queue_size - running_size
        waitting = waitting_t.count() -1
        message = dict(
            max_queue_size = max_queue_size,
            running_size = running_size,
            available = available,
            waitting = waitting,
            total_used = running_t.get_auto_incre() - 1
        )
        self.write(message)


class UserHandler(web.RequestHandler):
    def post(self):
        user_id = self.get_argument("user_id")
        result = backup_t.query(user_id=user_id)
        user_record = list()
        for line in result:
            temp = dict()
            temp['created_time'] = line['created_time']
            temp['instance_data'] = line['instance_data']
            try:
                temp['processed_time'] = line['processed_time']
            except:
                pass
            try:
                temp['deleted_time'] = line['deleted_time']
            except:
                pass
            user_record.append(temp)
        self.write({"history": user_record})


class StatusHandler(web.RequestHandler):
    def get(self):
        new_running_list = copy.deepcopy(running_list)
        for item in new_running_list:
            item['_oid'] = repr(item['_oid'])
        running_list_size = len(running_list)
        running_list_content = new_running_list
        timer_list_size = len(timer_list)
        
        auto_id_running = running_t.get_auto_incre()
        running_length = running_t.count()
        
        auto_id_waitting = waitting_t.get_auto_incre()
        waitting_length = waitting_t.count()
        
        # 获取所有用户排队的位置
        user_waitting = list()
        result = waitting_t.query()
        
        auto_id = waitting_t.get_auto_incre() - 1
        waitting = waitting_t.count() - 1
        deleted = auto_id - waitting
        for line in result:
            if line.has_key("instance_data"):
                temp_dic = dict()
                temp_list = list()
                temp_dic[line['user_id']] = line['auto_id'] - deleted
                temp_list.append(temp_dic)
                user_waitting.append(temp_list)
        
        result = dict(
            running_list_size = running_list_size,
            running_list_content = running_list_content,
            timer_list_size = timer_list_size,
            
            auto_id_running = auto_id_running,
            running_length = running_length,
            
            auto_id_waitting = auto_id_waitting,
            waitting_length = waitting_length,
            
            user_waitting = user_waitting
        )
        
        self.write(result)


def main(port, address):
    rebuild_timer_and_queue()
    
    putter_thread = RunningPutter()
    putter_thread.start()
    
    add_callback(update_nginx_host)
    
    app = iApplication()
    app.listen(port, address=address)
    ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main(options.server_port, options.server_listen)

