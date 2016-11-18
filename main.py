#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback
import bindparser
from tablestruct.table_struct import TableStructDic
from tablestruct.table_manage import singleton_manager


def get_parser(raw_sql):
    try:
        _sql = raw_sql.strip()
        _action = _sql[0:6].title()
        _cls = getattr(bindparser, "%sParser" % _action)
        return _cls(sql, singleton_manager)
    except Exception as e:
        print 'get_parser errmsg is %s' % traceback.format_exc()
        return None


if __name__ == '__main__':
    obj = TableStructDic(singleton_manager)
    obj.create()

    sql_list = [
        'select * from student_info_t where gender=:v1',
        'delete from student_info_t where name=:v1 and class=:v2',
        'update student_info_t set age=:v1, grade=:v2, class=:v3 where name=:v4',
        'insert into student_info_t(name, age, gender, grade, class, tel_num, create_date) values(:v1, :v2, "male", :v3, :v4, :v5, sysdate)',
    ]
    for sql in sql_list:
        print '*********************** handle sql %s *********************** ' % sql[0:6]
        print 'bind sentence for \r\n%s is:' % sql
        try:
            obj = get_parser(sql)
            obj.parse_sql()
        except:
            print 'get_parser for sql %s error, errmsg is %s' % (sql[0:6], traceback.format_exc())
            continue
