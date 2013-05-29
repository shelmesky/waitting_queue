#!/usr/bin/python
# --encoding:utf-8--

from mongo_driver import db_handler

# running_coll: 保存运行的请求
# waitting_coll: 保存在排队的请求
# instance_bak: 保存请求处理过程的记录
running_t = db_handler.running_coll
waitting_t = db_handler.waitting_coll
instance_bak = db_handler.running_coll_bak


class MongoExecuter(object):
    def __init__(self, collection):
        self.collection = collection
        self.auto_id_counts = "auto_increment_counts"
        self.init_auto_incre()
    
    def init_auto_incre(self):
        '''
        初始化collection内部的计数器
        '''
        if not self.collection.find_one({"f_type": self.auto_id_counts}):
            self.collection.insert({"f_type": self.auto_id_counts, "value": 1})
    
    def get_auto_incre(self):
        '''
        返回计数器的值
        '''
        auto_incre = self.collection.find_one({"f_type": self.auto_id_counts})
        return auto_incre["value"]
    
    def update_auto_incre(self):
        '''
        更新计数器
        '''
        auto_id = self.get_auto_incre()
        self.update(dict(f_type=self.auto_id_counts), value=auto_id + 1)
    
    def count(self):
        return self.collection.count()

    def query(self, **kwargs):
        '''
        在collection上执行一个查询
        作为一个生成器，返回查询到的记录
        '''
        return self.collection.find(kwargs)
    
    def query_one(self, **kwargs):
        '''
        在collection上执行一个查询
        作为字典，返回查询到的记录
        '''
        return self.collection.find_one(kwargs)

    def insert(self, **kwargs):
        '''
        插入记录，同时在记录中插入自增id
        返回记录的ObjectID
        '''
        auto_id = self.get_auto_incre()
        # 如果大于1000，collection内部的计数器清零
        if auto_id > 1000:
            self.update(dict(f_type=self.auto_id_counts), value=1)
            auto_id = 1
        kwargs.setdefault("auto_id", auto_id)
        obj_id = self.collection.insert(kwargs)
        self.update_auto_incre()
        return obj_id
    
    def update(self, condition=None, **contents):
        '''
        更新记录
        condition为条件，是一个字典
        contents为需要更新的内容
        '''
        if not condition:
            raise RuntimeError("Need *condition* parameter")
        self.collection.update(condition, {"$set": contents})

    def delete(self, **kwargs):
        '''
        删除指定的记录
        '''
        self.collection.remove(kwargs)


running_t_instance = MongoExecuter(running_t)
waitting_t_instance = MongoExecuter(waitting_t)
instance_backup = MongoExecuter(instance_bak)

