# -*- coding=utf-8 -*-

import os

# 当前目录
CUR_PATH = os.path.normpath(os.getcwd())
# 生成c结构体的建表语法
SYNTAX_FILE = os.path.normpath(os.path.join(CUR_PATH, 'table_struct.txt'))
# 日志信息
LOG_FILE = os.path.normpath(os.path.join(CUR_PATH, 'table_struct.log'))
# 存放根据建表语法生成的c结构体txt目录
STRUCT_DIR = os.path.normpath(os.path.join(CUR_PATH, 'struct_dir'))
# 持久化根据建表语法生成的结构体
STRUCT_PICKLE_FILE = os.path.normpath(
    os.path.join(CUR_PATH, 'tables_struct.pickle')
)
