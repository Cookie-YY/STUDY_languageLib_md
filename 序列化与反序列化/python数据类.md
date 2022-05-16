# 1. json
# 2. dataclass
1. 默认值可以赋值None
2. 没有指定默认值的必须赋值
    - Optional类型也不行
3. 没有强制类型校验（有提示）
~~~python
from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class Message:
    name: str
    age: int = 2
    # 可变类型通过factory赋值，否则多个Message共用一个list
    children: List[int] = field(default_factory=list)

msg = Message("a", 1)
msg_copy = dataclasses.replace(msg, age=2)  # 通过拷贝改变
print(dataclasses.astuple(msg))
print(dataclasses.asdict(msg))
print(inspect.getmembers(Message, inspect.isfunction))
~~~
**dataclass参数**
参数|意义
--|--
frozen=True|数据项不可变 msg.name="b"报错
order=True|顺序有意义（通过tuple比大小）

**field参数**
参数|意义
--|--
default_factory|默认值
repr=False|只是放在那里
hash=False|不参与hash
# 3 pydantic
1. 默认值可以赋值None
2. 类型是Optional的属性可以不赋值
3. 初始化参数不够时，会有报错信息，但不影响执行
3. 有强制类型校验（会尝试强转） 时间戳也可以转成时间
    - 可以从默认值推断类型
    - Optional[x] 是 Union[x, None]的快捷方式
~~~python
class User(pydantic.BaseModel):
    id: int  # 必须手动填
    name = 'John Doe'
    signup_ts: Optional[datetime]  # 默认值None
    friends: List[int] = []
    # 动态属性
    uid: UUID = Field(default_factory=uuid4)
    updated: datetime = Field(default_factory=datetime.utcnow)
    # 私有属性
    _processed_at: datetime = PrivateAttr(default_factory=datetime.now)

external_data = {
    'id': '123',
    'signup_ts': '2019-06-01 12:22',
    'friends': (1, 2, '3'),
}
try:
    user = User.parse_obj(external_data)
    user = User(**external_data)
    user = User.construct(**external_data)  # 不做验证，很快
    users = parse_obj_as(List[User], [external_data])
    # str 或 bytes
    user = User.parse_raw('{"id": 123, "signup_ts": "2019-06-01 12:22"}')
    # 高级用法：pickle
    user = User.parse_raw(
        pickle_data, content_type='application/pickle', allow_pickle=True
    )
    
except pydantic.ValidationError as e:
    print(e.json())
~~~
## 3.1 错误与验证
### 3.1.1 错误
1. 错误基类：ValidationError
2. 细分错误：ValueError、TypeError 或 AssertionError
~~~python
e.errors()        # dict类型
e.json(indent=2)  # str类型
str(e)
"""
[
    {
        'loc': ('foo',),
        'msg': 'value must be "bar"',
        'type': 'value_error',
    },
]
"""
~~~
### 3.1.2 验证
#### 3.1.2.1 装饰器
1. @validator('foo')修饰类方法，rasise响应的error
2. 方法是类方法，(cls, v, values)
3. values是个dict含有之前验证过的数据项
~~~python

from pydantic import BaseModel, ValidationError, validator

class Model(BaseModel):
    foo: str

    @validator('foo')
    def name_must_contain_space(cls, v, values):
        if v != 'bar':
            raise ValueError('value must be "bar"')
        return v

try:
    Model(foo='ber')
except ValidationError as e:
    print(e.errors())
    """
    [
        {
            'loc': ('foo',),
            'msg': 'value must be "bar"',
            'type': 'value_error',
        },
    ]
    """
~~~
#### 3.1.2.2 自定义error
~~~python
class NotABarError(PydanticValueError):
    code = 'not_a_bar'
    msg_template = 'value is not "bar", got "{wrong_value}"'


class Model(BaseModel):
    foo: str

    @validator('foo')
    def name_must_contain_space(cls, v):
        if v != 'bar':
            raise NotABarError(wrong_value=v)
        return v


try:
    Model(foo='ber')
except ValidationError as e:
    print(e.json())
    """
    [
      {
        "loc": [
          "foo"
        ],
        "msg": "value is not \"bar\", got \"ber\"",
        "type": "value_error.not_a_bar",
        "ctx": {
          "wrong_value": "ber"
        }
      }
    ]
    """
~~~

### 3.2 对象方法
~~~python
msg.dict() == dict(msg)
msg.json()
msg.copy()  # 浅拷贝
msg.schema()
msg.schema_json()
msg.__fields_set__  # 实例化时设置的值
msg.__config__  # 配置类

Msg.from_orm()   # orm模式 构建示例
Msg.parse_obj()
Msg.parse_raw()
Msg.parse_file()
Msg.construct()  # 非验证模式 构建示例
~~~
### 3.3 特殊类型
~~~python
# 时间
from datetime import datetime, date, timedelta
dt: Optional[datetime]
d: Optional[date]
td: Optional[timedelta]

# 1. datetime
# 时间戳
# 2020-01-01 10:10
# 2020-01-01 10:10:10

# 2. timedelta
# 数字字符串
# 整型、浮点型
# timedelta(days=1)
"""
1. td.total_seconds()   得到秒数
2. 通过时间戳实例化的datetime 含有时区数据
    无法和 2020-01-01 10:10类型直接相减
    now.tzinfo==None
    now=now.replace(tzinfo=pytz.timezone('UTC'))
    datetime.datetime(2016, 11, 13, 16, 23, 37, 488000, tzinfo=<UTC>)
"""
~~~