#!/usr/bin/python
# --encoding:utf-8--

from tornado import ioloop
from tornado import gen
from tornado import web
from tornado import httpclient
from tornado import httputil
import urllib

cloudopen_api = "http://127.0.0.1:8000"
cloudopen_api_create = "%s%s" % (cloudopen_api, "/create")
cloudopen_api_delete = "%s%s" % (cloudopen_api, "/delete")
cloudopen_api_query = "%s%s" % (cloudopen_api, "/query")

class iApplication(web.Application):
    def __init__(self):
        handlers = [
            (r"/", Main),
        ]
        
        web.Application.__init__(self, handlers)


class CloudOpenAPI(object):
    '''
    两种调用方法:
    1. 在RequestHandler中有父类CloudOpenAPI
    另外一个是实现on_[create delete query]_vm的重载，并调用self.write
    例如这样：
    class OnCreateVM(object):
        def on_create_vm(self, response):
            body = response.body
            if body:
                process(self, user_id, self.instance_data)
                self.write(body)
                self.finish()
    
    class CloudOpenAPI(object):
        def create_vm(self, user_id, instance_data):
            self.user_id = user_id
            self.instance_data = instance_data
            http_client.fetch(url, self.on_create_vm)
    
    class Main(web.RequestHandler, CloudOpenAPI, OnCreateVM):
        @web.asynchronous
        def post(self):
            self.create_vm(user_id, instance_data)
            
    
    
    2. 在其他类中调用
    作为类的父类之一
    例如:
    class RunningPutter(CloudOpenAPI):
        def run(self):
            self.create_vm(...)
        
        def on_create_vm(self, response):
            pass
    '''
    def make_request(self, url, method, body=None):
        headers = httputil.HTTPHeaders()
        headers.add('Accept', 'application/json')
        if method == "GET":
            request = httpclient.HTTPRequest(
                url = url,
                method = method,
                connect_timeout = 3,
            )
        elif body is not None:
            headers.add('Content-type', 'application/x-www-form-urlencoded')
            if isinstance(body, dict):
                body = urllib.urlencode(body)
                request = httpclient.HTTPRequest(
                    url = url,
                    method = method,
                    connect_timeout = 3,
                    body = body
                )
                
        return request
    
    def start(self, request, callback):
        client = httpclient.AsyncHTTPClient()
        client.fetch(request, callback)

    def create_vm(self, user_id, server_os, server_name):
        #user_id = vm['user_id']
        #instance_data = vm['instance_data']
        #server_os = instance_data['os']
        #server_name = instance_data['name']
        
        body = dict()
        body.setdefault('user_id', user_id)
        body.setdefault('os', server_os)
        body.setdefault('name', server_name)
        request = self.make_request(cloudopen_api_create, "POST", body)
        self.start(request, self.on_create_vm)
    
    def delete_vm(self, instance_id):
        body = dict()
        body.setdefault('id', instance_id)
        request = self.make_request(cloudope_api_delete, "POST", body)
        self.start(request, self.on_delete_vm)

    def query_vm(self, instance_id):
        body = dict()
        body.setdefault('id', instance_id)
        request = self.make_request(cloudope_api_query, "POST", body)
        self.start(request, self.on_query_vm)
    
    def on_create_vm(self, response):
        #raise NotImplementedError
        self.write(response.body)
        self.finish()
    
    def on_delete_vm(self, response):
        raise NotImplementedError
    
    def on_query_vm(self, response):
        raise NotImplementedError
    

class Main(web.RequestHandler, CloudOpenAPI):
    @web.asynchronous
    def get(self):
        self.create_vm("123", "linux", "test_linux")
    

if __name__ == '__main__':
    app = iApplication()
    app.listen(9899)
    ioloop.IOLoop.instance().start()

