#!/usr/bin/python
# --encoding:utf-8--

import httplib2
import urllib
import logging
import copy
import json
import sys
import simplejson

from common.logger import LOG


class Client(object):
    def __init__(self, api):
        self.api = api
    
    def createInstance(self, user_id, os=None, name=None):
        url = '/api/instance/add/'
        content = {'user_id': user_id,
                   'os': os,
                   'name': name}
        resp, body = self.api.post(url, body=content)
        return resp, body
    
    def deleteInstance(self, instance_id):
        url = "/api/instance/delete/"
        content = {'id': instance_id}
        resp, body = self.api.post(url, body=content)
        return resp, body
    
    def queryInstance(self, instance_id):
        url = "/api/instance/"
        content = {"id": instance_id}
        resp, body = self.api.post(url, body=content)
        return resp, body
    

class HTTPClient(httplib2.Http):
    def __init__(self, username=None, password=None,
                 api_url=None, token=None, timeout=None):
        super(HTTPClient, self).__init__(timeout=timeout)
        self.username = username
        self.password = password
        self.api_url  = api_url
        self.token = token
        
    def authenticate(self):
        raise NotImplementedError
        
    def request(self, url, method, **kwargs):
        reload(sys)
        sys.setdefaultencoding('UTF-8')
        request_kwargs = copy.copy(kwargs)
        request_kwargs.setdefault('headers', kwargs.get('headers', {}))
        request_kwargs['headers']['Accept'] = 'application/json'
        request_kwargs['headers']['Content-type'] = 'application/x-www-form-urlencoded'
        request_kwargs['body'] = urllib.urlencode(kwargs['body'])
        resp, body = super(HTTPClient, self).request(self.api_url + url,
                                                     method, **request_kwargs)
        return resp, body


class _cloudopen_api_client(HTTPClient):
    def __init__(self, **kwargs):
        super(_cloudopen_api_client, self).__init__(**kwargs)
        self.interface = Client(self)
    
    def post(self, url, **kwargs):
        return self.request(url, 'POST', **kwargs)
    
    def get(self, url, **kwargs):
        return self.request(url,'GET',**kwargs)
