#!/usr/bin/python
# --encoding:utf-8--

from tornado.options import options
from http_client import _cloudopen_api_client

api_url = options.cloudopen_api_url


def _cloudopen_client(api_url):
    return _cloudopen_api_client(api_url=api_url)


def createInstance(user_id=None, os=None, name=None):
    return _cloudopen_client(api_url).interface.createInstance(user_id, os, name)


def deleteInstance(instance_id):
    return _cloudopen_client(api_url).interface.deleteInstance(instance_id)


def queryInstance(instance_id):
    return _cloudopen_client(api_url).interface.queryInstance(instance_id)