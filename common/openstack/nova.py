import sys
import simplejson as json
from common.utils import from_now_to_datetime
from common.logger import LOG
from common.openstack import http_api as api


def create_vm(vm):
    user_id = vm['user_id']
    instance_data = vm['instance_data']
    server_os = instance_data['os']
    server_name = instance_data['name']
    resp, body = api.createInstance(user_id, server_os, server_name)
    LOG.info("Cloudopen create instance: %s %s %s" % (user_id, server_os, server_name))
    LOG.info("Got return from cloudopen: %s" % body)
    body = json.loads(body)
    instance_id = body['instance_id']
    return instance_id


def delete_vm(instance_id):
    resp, body = api.deleteInstance(instance_id)
    body = json.loads(body)
    msg = body['msg']
    LOG.info("%s vm deleted: %s" % (from_now_to_datetime(), instance_id))
    LOG.info("Got return from cloudopen: %s" % msg)
    return msg


def query_vm(instance_id):
    resp, body = api.queryInstance(instance_id)
    body = json.loads(body)
    if body.has_key("ips"):
        ips = body.get("ips")
        private = ips.get("private")
        if private:
            ip_addr = private[0].get("addr")
            if ip_addr:
                return ip_addr
