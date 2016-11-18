#!/usr/bin/env python
# -*- coding: utf-8 -*-


class ParseTool(object):
    action = None

    def __init__(self, sql, tb_manager):
        super(ParseTool, self).__init__()
        self.table_manage = tb_manager

        self._simplify_sql(sql)
        self._get_info_from_sql()
        self._get_struct()

    @property
    def sql(self):
        return self._sql

    @property
    def table_name(self):
        return self._table_name

    def _simplify_sql(self, sql):
        """
        将sql语句转换为小写，并且将group by和order by截去
        """
        new_sql = sql.strip().lower()
        pos = new_sql.find("group by")
        if pos != -1:
            new_sql = new_sql[:pos]

        self._sql = new_sql.strip()

    def _get_info_from_sql(self):
        """
        获取sql语句中的一些基本信息
        """
        self._pos_from = self._sql.find('from')
        if self._pos_from == -1:
            raise Exception('incorrect format, sql is %s' % self._sql)

        self._pos_where = self._sql.find('where')
        if self._pos_where == -1:
            self._table_name = self._sql[self._pos_from+len("from"):].strip()
        else:
            self._table_name = self._sql[self._pos_from+len("from"):self._pos_where].strip()

    def _get_struct(self):
        """
        根据表名获取本地文件中的struct信息
        """
        self._tb_struct = self.table_manage.get_struct_from_dump(self._table_name)
        if not self._tb_struct:
            error = 'please create struct for table %s, use tableStruct.py' % \
                    self._table_name
            raise Exception(error)

    def _get_columns(self):
        """
        返回表结构中的column列表
        """
        return [_ for _ in self._tb_struct.keys() if not _.startswith('$')]

    def parse_sql(self):
        """
        override
        """

    def gen_sentences(self, bind_list, bind_in=True):
        """
        根据sql中的字段，生成bind语句。默认为bindin
        """
        cnt = 1
        for item in bind_list:
            self.gen_single_sentence(item.strip(), cnt, bind_in)
            cnt += 1

    def gen_single_sentence(self, column, cnt, bind_in):
        """
        生成一个bind语句字符串，函数运行如下
        BindIn(int32_t nPos, void *pVal, EFieldType nColType,
            uint32_t nColLen, uint32_t nStructSize)
        或者
        BindOut(int32_t nPos, void *pVal, EFieldType nColType,
            uint32_t nColLen, uint32_t nStructSize)
        函数参数nPos表示绑定位置，pVal表示绑定地址，nColType表示数据类型，
        nColLen表示长度，nStructSize表示结构体大小
        """
        column_info = self._tb_struct.get(column)
        if not column_info:
            raise Exception('table %s does not contain column %s' %
                            (self._table_name, column))

        # bind语句中的变量如下
        str_point_val = ''
        str_col_type = ''
        str_col_len = ''
        str_struct_size = ''

        col_name, col_type, col_length = \
            column_info[0], column_info[3], column_info[4]

        struct_name = self._tb_struct['$struct_name']

        if col_type == 'number':
            (str_col_type, str_col_len) = ('FIELD_INT32', 'sizeof(int32_t)') \
                if col_length <= 9 else ('FIELD_INT64', 'sizeof(int64_t)')

            (str_point_val, str_struct_size) = ('&' + col_name, str_col_len) \
                if bind_in else ('&' + struct_name + '.' + col_name,
                                 'sizeof(' + struct_name + ')')

        elif col_type == 'varchar2' or col_type == 'date':
            str_col_type = 'FIELD_CHAR'
            str_col_len = 'sizeof(' + col_name + ')'

            (str_point_val, str_struct_size) = (col_name, str_col_len) \
                if bind_in else (struct_name + '.' + col_name,
                                 'sizeof(' + struct_name + ')')

        str_line = 'BindIn' if bind_in else 'BindOut'
        str_line += '('
        str_line += str(cnt)
        str_line += ', '
        str_line += str_point_val + ', ' + str_col_type + ', ' + str_col_len + \
                    ', ' + str_struct_size + ')' + ';'

        print(str_line)
        str_line += '\n'

        return str_line

    @staticmethod
    def parse_bind_in(lst):
        """
        对于select/delete/update语句中的绑定语法 value=:v，进行分解，提取出'='前的列名，
        生成绑定字段的列表并返回
        """
        bind_in_list = []

        for item in lst:
            # select/delete/update where子句中包含绑定语句类似value = :v
            if ':' in item:
                pos = item.find('=')
                if pos != -1:
                    column = item[:pos].strip()
                else:
                    continue

                bind_in_list.append(column)

        return bind_in_list


class SelectParser(ParseTool):
    action = 'Select'

    def __init__(self, sql, tb_manager):
        super(SelectParser, self).__init__(sql, tb_manager)

    def parse_sql(self):
        """
        对于select语句：
        select name, age, gender, grade, class from
            student_info_t where name = :v1 and class = :v2
        1对select和from之间子句中的字段，生成对应的bindOut语句
        2对where子句中的绑定语句进行分解，生成对应的bindIn语句
        """
        bind_out_list = self.sql[len("select"):self._pos_from].split(',')

        if len(bind_out_list) == 1 and bind_out_list[0].strip() == '*':
            # select * from table where condition=xxx
            bind_out_list = self._get_columns()

        self.gen_sentences(bind_out_list, bind_in=False)
        if self._pos_where != -1:
            # sql中有where子句，需要对where子句中的条件进行bind_in
            where_condition_list = self.sql[self._pos_where+len("where"):].split("and")
            bind_in_list = self.parse_bind_in(where_condition_list)
            self.gen_sentences(bind_in_list)


class DeleteParser(ParseTool):
    action = 'Delete'

    def __init__(self, sql, tb_manager):
        super(DeleteParser, self).__init__(sql, tb_manager)

    def parse_sql(self):
        """
        对于delete语句：
        delete from student_info_t where name=:v1 and class=:v2
        将where子句中的字段取出，生成对应的bindIn语句
        """
        where_condition_list = self.sql[self._pos_where+len("where"):].split("and")
        bind_in_list = self.parse_bind_in(where_condition_list)
        self.gen_sentences(bind_in_list)


class InsertParser(ParseTool):
    action = 'Insert'

    def __init__(self, sql, tb_manager):
        super(InsertParser, self).__init__(sql, tb_manager)

    def _get_info_from_sql(self):
        if self._sql.count('(') != 2 or self._sql.count(')') != 2:
            raise Exception('incorrect format, sql is %s' % self._sql)

        # 获取insert语句中的关键位置
        self._pos_into = self._sql.find("into")
        self._pos_column_pre = self._sql.find("(")
        self._pos_column_post = self._sql.find(")")
        self._pos_values = self._sql.find("values")
        if -1 in [self._pos_into, self._pos_column_pre, self._pos_column_post,
                  self._pos_values]:
            raise Exception('incorrect format, sql is %s' % self._sql)

        self._table_name = self._sql[self._pos_into+len("into"):
                                     self._pos_column_pre].strip()

    def parse_sql(self):
        """
        对于insert语句：
        insert into student_info_t (name, age, gender, grade,
            class, tel_num, created_date)
        values (:col1, :col2, :col3, :col4,
            :col5, :col6, sysdate )
        将values前后两个括号里的值分别提取出column_list和bind_list，
        如果bind_list中的元素包含':'，
        那么说明此字段需要进行绑定，插入rawLst，生成对应的bindIn语句
        """
        # values之前的括号中的值，表示要插入的列column
        column_list = self._sql[self._pos_column_pre+1:self._pos_column_post].strip().split(",")

        # values之后的括号得值，表示要插入列的值
        value_list = self.sql[self._pos_values+len("values"):].strip(" ()").split(",")
        if len(column_list) != len(value_list):
            raise Exception("insert column not match bind list")

        bind_in_list = [column_list[i] for i, value in enumerate(value_list) if ':' in value]
        self.gen_sentences(bind_in_list)


class UpdateParser(ParseTool):
    action = 'Update'

    def __init__(self, sql, tb_manager):
        super(UpdateParser, self).__init__(sql, tb_manager)

    def _get_info_from_sql(self):
        self._pos_set = self._sql.find("set")
        if self._pos_set == -1:
            raise Exception('no set in sql %s' % self._sql)

        self._pos_where = self._sql.find("where")
        self._table_name = self._sql[len("update"):self._pos_set].strip()

    def parse_sql(self):
        """
        对于update语句:
        update student_info_t set grade = :v1,
         where name = :v2 and class = :v3
        1 对set和where之间子句中的字段，根据字段与字典中的结构生成对应的bindIn第一部分语句
        2 对where后的子句，根据字段与字典中的结构生成对应的bindIn第二部分语句
        """
        if self._pos_where == -1:
            raw_list = self.sql[self._pos_set+len("set")].split(",")
        else:
            raw_list = self.sql[self._pos_set+len("set"):self._pos_where].split(",")
            raw_list.extend(self.sql[self._pos_where+len("where"):].split("and"))

        bind_in_list = self.parse_bind_in(raw_list)
        self.gen_sentences(bind_in_list)
