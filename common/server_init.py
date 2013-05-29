from tornado.options import define, options
import tornado.options

conf_file = "server.conf"

def server_init():
    define("server_listen", help="while address that server will listen", type=str)
    define("server_port", help="server will run on given port", type=int)
    define("server_debug_level", help="server debug level", type=str)
    
    define("multicast_addr", help="multicast group", type=str)
    define("multicast_port", help="port of multicast group", type=int)
    define("multicast_bind_addr", help="multicast bind addr", type=str)
    
    define("instance_survive_times", help="how long instance will survive", type=int)
    define("running_dict_size", help="the size of running queue", type=int)
    define("waitting_queue_size", help="the size of waitting queue", type=int)
    
    define("cloudopen_api_url", help="api server of cloudopen", type=str)
    
    define("mongo_uri", help="connection uri for mongodb", type=str)
    define("mongo_db", help="database used in mongodb", type=str)
    define("mongo_conn_pool_size", help="connection pool size", type=int)
    define("mongo_conn_timeout", help="connnection timeout seconds", type=int)
    
    tornado.options.parse_config_file(conf_file)