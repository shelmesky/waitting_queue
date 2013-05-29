#!/usr/bin/python
# --encoding:utf-8--

from tornado.options import options
import pymongo
#from common.logger import LOG


class MongoDBDriver(object):
    def __init__(self, mongo_uri, **kwargs):
        self.mongo_uri = mongo_uri
        self.conn_pool_size = kwargs.get("conn_pool_size", 512)
        self.conn_timeout = kwargs.get("conn_timeout", 2)
    
    def connect(self):
        '''
        返回mongodb的连接对象
        '''
        try:
            self.connection = pymongo.Connection(host=self.mongo_uri,
                                                max_pool_size=self.conn_pool_size,
                                                network_timeout=self.conn_timeout)
        except Exception, e:
            raise
    
    def close(self):
        self.connection.close()


driver = MongoDBDriver(options.mongo_uri,
                       conn_pool_size=options.mongo_conn_pool_size,
                       conn_timeout=options.mongo_conn_timeout)
driver.connect()
conn = driver.connection
# db的连接对象
db_handler = conn[options.mongo_db]


if __name__ == '__main__':
    # make simple test
    driver = MongoDBDriver("mongodb://admin:admin@127.0.0.1:27017/cloudopen",
                           conn_pool=512,
                           conn_timeout=2)
    driver.connect()
    conn = driver.connection
    db = conn['cloudopen']
    test_coll = db.test_collections
    test_coll.insert({"key": "value"})
    print test_coll.find_one()
    