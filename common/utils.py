# --encoding:utf-8--

import datetime

def from_now_to_datetime(time_format=None, **kwargs):
    '''
    计算从现在开始到某一个时间，返回格式化之后的时间字符串
    days = 1 一天之后
    seconds = 60 60秒之后
    time_format = None 格式化参数，默认为: %Y-%m-%d %H:%M:%S
    不带参数调用则输出当前时间的格式化字符串
    '''
    if not time_format:
        time_format = "%Y-%m-%d %H:%M:%S"
    days = kwargs.get("days", 0)
    seconds = kwargs.get("seconds", 0)
    now = datetime.datetime.now()
    result = now + datetime.timedelta(days=days, seconds=seconds)
    return result.strftime(time_format)


def cal_seconds_to(time_str=None, time_format=None):
    '''
    计算从现在开始, 还有多少秒到之后的某个时间点
    返回int类型的秒数
    time_str 需要计算的时间点
    time_format 输入的时间字符串格式，默认假设为: %Y-%m-%d %H:%M:%S
    '''
    if not time_str:
        raise RuntimeError("Need time_str argument.")
    if not time_format:
        time_format = "%Y-%m-%d %H:%M:%S"
    try:
        future_time = datetime.datetime.strptime(time_str, time_format)
    except ValueError, e:
        raise
    now = datetime.datetime.now()
    try:
        result = future_time - now
        return result.total_seconds()
    except Exception, e:
        raise

