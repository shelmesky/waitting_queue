from sender import sender
from common.mongo_api import running_t_instance as running_t
from common.logger import LOG


def update_nginx_host(conn):
    data, address = conn.recvfrom(2048)
    data = eval(data)
    node_id = data['node_id']
    msg_type = data['msg_type']
    if node_id != "client" and msg_type != "heartbeat":
        LOG.info("Receive from multicast: %s" % data)
        instance_id = data['msg_id']
        host = data['target_host']
        port = data['target_port']
        running_t.update(dict(uuid=instance_id),
                        host=host, port=port)


def add_nginx_host(instance_id=None, host=None, port=None):
    msg_id = instance_id
    msg_type = "add"
    node_id = "client"
    message = dict(
        msg_type = msg_type,
        msg_id = msg_id,
        dst_host = host,
        dst_port = port,
        node_id = node_id
    )
    message = str(message)
    sender(message)
    LOG.info("Send to multicast: %s" % message)


def del_nginx_host(instance_id=None):
    msg_id = instance_id
    msg_type = "del"
    node_id = "client"
    result = running_t.query_one(uuid=instance_id)
    try:
        port = result['port']
    except KeyError:
        LOG.info("Error occured in get port.")
        return
    message = dict(
        msg_type = msg_type,
        msg_id = msg_id,
        server = port,
        node_id = node_id
    )
    message = str(message)
    sender(message)
    LOG.info("Send to multicast: %s" % message)
