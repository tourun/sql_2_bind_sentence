# -*- coding:utf-8 -*-

import pickle
import logging
import traceback
import collections
import sql_2_bind_sentence.conf

logger = None


def init_log():
    """
    初始化全局logger对象
    """
    global logger
    logger = logging.getLogger('table')
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(process)d|%(asctime)s|%(filename)s|%(lineno)d|%(message)s"
    )
    shd = logging.StreamHandler()
    shd.setLevel(logging.DEBUG)
    shd.setFormatter(fmt)
    fhd = logging.FileHandler(filename=sql_2_bind_sentence.conf.LOG_FILE, encoding='utf-8', mode='a')
    fhd.setFormatter(fmt)
    fhd.setLevel(logging.DEBUG)

    logger.addHandler(fhd)
    logger.addHandler(shd)


class TableManage(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TableManage, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        init_log()
        self._get_dumps_dict()

    def _get_dumps_dict(self):
        """
        加载持久化数据对象
        """
        try:
            with open(sql_2_bind_sentence.conf.STRUCT_PICKLE_FILE, 'rb') as stf:
                self._dump_dict = pickle.load(stf)
        except IOError:
            logger.warning(traceback.format_exc())
            self._dump_dict = dict()

    def dump_to_pickle(self, table_name, tb_struct):
        """
        将生成好的结构体持久化到本地
        """
        self._dump_dict[table_name] = tb_struct
        with open(sql_2_bind_sentence.conf.STRUCT_PICKLE_FILE, 'wb') as stf:
            pickle.dump(self._dump_dict, stf)

    def get_struct_from_dump(self, table_name):
        """
        从持久化数据中获取table对应的结构体
        """
        return self._dump_dict.get(table_name, collections.OrderedDict())

    def remove_struct_from_dump(self, table_name):
        """
        删除table对应的结构体
        """
        self._dump_dict.pop(table_name, None)

    def get_all_tablenames(self):
        """
        获取持久化对象中已存在的表
        """
        return self._dump_dict.keys()


singleton_manager = TableManage()
