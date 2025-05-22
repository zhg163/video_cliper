# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2022/5/31 4:35 PM

# File_name: 'config.py'

"""
Describe: this is a demo!
"""


from easydict import EasyDict as edict

__C = edict()
cfg = __C

# database config
__C.DBCONFIG = edict()
__C.DBCONFIG.MINCACHED = 5
__C.DBCONFIG.MAXCACHED = 10
__C.DBCONFIG.MAXCONNECTIONS = 50
__C.DBCONFIG.BLOCKING = True
__C.DBCONFIG.MAXSHARED = 51

# __C.DBCONFIG.HOST = "111.231.114.205"
# __C.DBCONFIG.PORT = 9208
# __C.DBCONFIG.USER = "root"
# __C.DBCONFIG.PASSWD = "MySql@hangzhou+2017"
# __C.DBCONFIG.DBNAME = "robot_outbound"
# __C.DBCONFIG.CHARSET = "utf8"
#本地
__C.DBCONFIG.HOST = "192.168.0.251"
__C.DBCONFIG.PORT = 3306
__C.DBCONFIG.USER = "bankdev"
__C.DBCONFIG.PASSWD = "my@shargoodata2025"
__C.DBCONFIG.DBNAME = "xuegu_spd"
__C.DBCONFIG.CHARSET = "utf8"


model_url = "http://loction.cpolar.top/offline_trade_model/find_address"
process_status_url = 'http://loction.cpolar.top/offline_trade_model/get_status'
time_out = 60  #10min


