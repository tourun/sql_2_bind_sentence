关于
---
####这是之前工作中，为了减少重复工作创建的一个小程序，实现功能有：
* 根据建表语法生成对应的c-struct结构体，并且将其存储在本地的pickle文件中
* 根据select/insert/update/delete语句，生成对应的bind语句，调用封装好的Oracle-OCI函数，完成数据库的增删改查操作

生成c-struct结构体
---
根据建表语法生成c-struct结构体，在生成程序中，为体现列名的数据类型，在变量名前加上标识，表示具体的数据类型。在对表的column转换时，根据下面规则进行：

|列名    |类型        |对应的c程序数据类型 |生成结构体中的列名|
|------ |--------    |-----------------|---------------|
|Name   |varchar2(16)|char             |szName          |
|Age    |Number(9）  |int32_t          |nAge           |
|Tel    |Number(16)  |int64_t          |lTel            |
|Create_Date|Date     |char              |szCreateDate|

假设上面结构体对应的表名是student_info_t，那么生成的c-struct名为 tStudentInfo.将建表语法写入table_struct.txt文件中，使用TableStructDic对象调用进行，构造TableStructDict对象时，需要使用全局的table管理对象singleton_manager

```python
from tablestruct.table_struct import TableStructDic
from tablestruct.table_manage import singleton_manager


if __name == "__main__:
    obj = TableStructDic(singleton_manager)
    obj.create()
```
生成的c-struct结构体文件会写入struct_dir目录

生成bind语句
---
通过自定义的bind语句操作Oracle-OCI语句，实现对数据库的增删改查操作。对于语句 ：
> select Name, Age, Tel from student_info_t where class=:v1   //:v1表示位置参数

要查找的列需要用bindout语句进行绑定，而where条件子句需要用bindin语句进行绑定，bind语句原型：
> int32_t BindOut(int32_t nPos, void *pVal, EFieldType nType, uint32_t nColLen, uint32_t nStructSize);

> int32_t BindIn(int32_t nPos, void *pVal, EFieldType nColType, uint32_t nColLen, uint32_t nStructSize);

> 参数及含义：nPos 绑定位置，pVal 绑定地址，nColType 数据类型，nColLen 长度， nStructSize 结构体大小

对于上述的select语句，那么程序运行之后会生成对应的bind语句如下：
> BindOut(1, tStudentInfo.szName, FIELD_CHAR, sizeof(szName), sizeof(tStudentInfo));

> BindOut(2, &tStudentInfo.nAge, FIELD_INT32, sizeof(int32_t), sizeof(tStudentInfo));

> BindOut(3, tStudentInfo.szTel, FIELD_CHAR, sizeof(szTelNum), sizeof(tStudentInfo));

> BindIn(1, szClass, FIELD_CHAR, sizeof(szClass), sizeof(szClass));

程序会根据Select/Insert/Update/Delete，动态生成对应的Parser进行解析，生成bind语句
