# -*- coding:utf-8 -*-

import logging
import os
import re
import traceback
from sql_2_bind_sentence import conf

logger = logging.getLogger('table')


class TableStructDic(object):

    pattern = re.compile(r'\b[\w]+\b')

    def __init__(self, tb_manager):
        super(TableStructDic, self).__init__()
        self._struct = None
        self.table_manager = tb_manager

    @property
    def struct(self):
        return self._struct

    def _create_struct(self, table_name, column_list):
        """
        根据列信息，创建table对应的数据结构
        """
        if not self._struct:
            # _struct不存在时，重新构造
            # table_name/struct_name/file_name 几个关键字的key使用$前缀，与列名区分
            self._struct['$table_name'] = table_name
            struct_name = self._get_struct_name(table_name, from_column=False)
            self._struct['$struct_name'] = struct_name
            # 解析除过create table的句子
            self._parse_each_line(column_list[1:])
            
            self.table_manager.dump_to_pickle(table_name, self._struct)

        self._create_struct_file()

    def _parse_each_line(self, column_list):
        """
        根据建表语法中的每列的描述信息，创建对应的变量
        """
        for line in column_list:
            try:
                line = line.strip().lower()
                if line == ')' or line == ');':
                    break
                if line == '(':
                    continue

                items = self.pattern.findall(line)
                col_name, col_type, col_length = \
                    items[0], items[1], items[2]

                if not col_length.isdigit():
                    # date类型
                    col_length = '14'
                self._create_struct_item(col_name, col_type, int(col_length))
            except Exception as e:
                logger.error(str(e))
                logger.error(traceback.format_exc())

    def _create_struct_item(self, col_name, col_type, col_length):
        """
        根据表的列名生成结构体的表名/字段，
        生成规则为将'_'分隔开的每个单词的第一个字母大写后，连接在一起，
        比如根据task_type_id number(9)生成nTaskTypeId
        并生成(结构体名，结构体类型，结构体长度，列类型，列长度)的五元组，
        放入dictionary
        key表示表中的列名column，
        value为根据type和length转换后的列名、类型、长度、表中原始type、原始length 组成的5个元素的元组
        如'region_id number(10)'被转换为('lRegionId', 'int64_t', '', 'number', 10)
        而'state varchar2(3)'被转换为('szState', 'char', '[4]', varchar2, 3)
        """
        file_name = 'struct_' + self._struct['$table_name'] + '.txt'
        self._struct['$file_name'] = file_name

        field_name = self._get_struct_name(col_name)
        field_type = ''
        field_length = ''
        if col_type == 'number':
            if col_length <= 9:
                field_name = 'n' + field_name
                field_type = 'int32_t'
            else:
                field_name = 'l' + field_name
                field_type = 'int64_t'
        elif col_type == 'varchar2' or col_type == 'date':
            field_name = 'sz' + field_name
            field_type = 'char'
            field_length = '[' + str(col_length + 1) + ']'

        self._struct[col_name] = (
            field_name,
            field_type,
            field_length,
            col_type,
            col_length
        )

    def _create_struct_file(self):
        """
        根据table建表语法生成对应的struct文件
        """
        if not os.path.exists(conf.STRUCT_DIR):
            os.mkdir(conf.STRUCT_DIR)

        file_path = os.path.normpath(
            os.path.join(
                conf.STRUCT_DIR,
                self._struct['$file_name']
            )
        )
        with open(file_path, 'wb') as tf:
            lines = ''
            lines += 'struct ' + self._struct['$struct_name'] + '\r\n'
            lines += '{' + '\r\n'

            for key, value in self._struct.items():
                if key in ['$table_name', '$struct_name', '$file_name']:
                    continue
                lines += '\t'
                field_name, field_type, field_length = \
                    value[0], value[1], value[2]
                if field_length:
                    lines += ' '.join([field_type, field_name, field_length])
                else:
                    lines += ' '.join([field_type, field_name])

                lines += ';\r\n'

            lines += '};'
            tf.write(lines)

    @staticmethod
    def _read_syntax_file():
        """
        读取建表语法，返回列信息
        """
        column_list = []
        try:
            with open(conf.SYNTAX_FILE, 'rb') as tf:
                column_list = tf.readlines()
                column_list = filter(lambda l: l.strip(), column_list)
        except IOError:
            logger.error(traceback.format_exc())

        return column_list

    def create(self):
        """
        对建表语法进行分析，生成字典
        """
        column_list = self._read_syntax_file()
        table_name = self.get_tablename(column_list[0])
        if not column_list or not table_name:
            logger.error('table_struct.txt format error')
            return

        self._struct = self.table_manager.get_struct_from_dump(table_name)
        struct_file_name = self._struct.get('file_name', '')
        if struct_file_name and self._exist_struct_file(struct_file_name):
            logger.info("%s already exists", struct_file_name)
            return

        self._create_struct(table_name, column_list)

    def reload_table(self):
        """
        重新加载表的结构
        """
        column_list = self._read_syntax_file()
        table_name = self.get_tablename(column_list[0])
        if not column_list or not table_name:
            logger.error('table_struct.txt format error')
            return

        self._create_struct(table_name, column_list)
        self.table_manager.remove_struct_from_dump(table_name)

    @staticmethod
    def _exist_struct_file(file_name):
        """
        是否已生成建表语法对应的结构体文件
        """
        if os.path.exists(conf.STRUCT_DIR):
            for f in os.listdir(conf.STRUCT_DIR):
                if f == file_name:
                    return True
        return False

    @staticmethod
    def get_tablename(line):
        """
        获取表名
        """
        if 'create table' not in line:
            return ''

        table_name = line[len('create table'):].strip().lower()
        if '.' in table_name:
            # 如果建表语法中有库名或者用户名，去掉dot号
            table_name = table_name[table_name.find('.') + 1:]

        return table_name

    @staticmethod
    def _get_struct_name(col_name, from_column=True):
        """
        根据表的列名生成结构体的字段，生成规则为将'_'分隔开的每个单词的第一个字母大写后，
        连接在一起
        """
        lst = col_name.split('_')

        if lst[-1] == 't':
            # 表名如果以t结尾，不体现在结构体名中
            lst = lst[0:-1]

        struct_name = reduce(lambda s, l: ''.join([s, l[0].upper() + l[1:]]),
                             lst,
                             '')

        return struct_name if from_column else 't' + struct_name
