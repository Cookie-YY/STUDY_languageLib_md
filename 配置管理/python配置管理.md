# 1. dynaconf
## 1.1 配置文件加载
1. 实例化参数：settings_files = ['conf/settings.dev.toml']
2. 环境变量：ENV_FOR_DYNACONF=dev
~~~toml
[dev]
env = "dev"  # settings["env"]

[dev.time]
tz = "Asia/Shanghai"  # settings["time"]["tz"]
format = "YYYY-MM-DD HH:mm:ss ZZ"  # settings["time"]["format"]

[dev.redis]
url = "redis://?db=0"  # settings["redis"]["url"]
~~~
## 1.2 环境变量加载
1. 实例化参数：environments=True,
2. 实例化参数：envvar_prefix='MODELSERVER'
3. 如果手动注入需要 settings.configure()
    - 手动注入：os.environ.setdefault("key", "value")
4. MODELSERVER_VAR2__VAR3: 字典的第二层要用双下划线
~~~python
# monkeypatch pytest的写法
monkeypatch.setenv('MODELSERVER_VAR2__VAR3', 'world')
settings.configure()
assert settings.var2.var3 == 'world'
~~~
## 附录：实例化的代码
~~~python
# dynaconf = "^3.1.8"
from dynaconf import Dynaconf

settings = Dynaconf(
    environments=True,  # 可以从环境变量中加载配置
    envvar_prefix='MODELSERVER',  # 只认envvar_prefix开头的环境变量
    settings_files=[  # 写法固定，配置环境变量ENV_FOR_DYNACONF=dev
        'conf/settings.dev.toml',
        'conf/settings.pytest.toml',
        'conf/settings.boe.toml',
        'conf/settings.staging.toml',
        'conf/settings.prod.toml',
    ]
)
~~~

# 2. yml
1. 支持引用
2. 支持null
3. 支持include
## 2.1 使用
~~~python
# PyYAML = "==6.0"
from yaml import load, Loader
with open(config_path, 'r', encoding="utf-8") as f:
    config = load(file, Loader=Loader)
config["base"]["top"]
~~~
## 2.2 yml示例
~~~yml
# 字典
mapping: {'id':'时序点', 'fluctuation':'波动幅度', 'trend':"趋势斜率", 'seasonality':'周期','level':'中位数水平',
          'max':'最大值', 'min':'最小值', 'mean':'平均值', 'span':'最值跨度比例'}
mapping:
  top: 3
# 数组
types: [null, 'Anomaly', 'Fluctuation']
# 继承
defaults: &defaults
  adapter:  postgres
  host:     localhost

development:
  database: myapp_development
  <<: *defaults
# 引用
basic:
  top: 3  # how many top insights will be pushed for each type
  reverser_top: 3  # how many top reversers will be output
  pid_w: &pid_w 0.2  # weight for percentage of insight data
  ct_w: &ct_w 0.4  # weight for category of insight type
  nt_w: &nt_w 0.4  # weight for uncommonness degree
  weights: [*ct_w, *pid_w, *nt_w]
  decay_points: 0.1
  decay_insights: 0.1
  epsilon: !!float 1e-7
  metric_round: 3
~~~

# 3. environment + params
## 3.1 environment
1. 定义不同的方法，根据环境变量返回结果
~~~python
import os

def is_online() -> bool:
    online = (os.getenv('ZELDA_INSIGHT_ONLINE') is not None) and (os.getenv('ZELDA_INSIGHT_ONLINE').strip() == '1')
    return online

def is_local() -> bool:
    return (os.getenv('ZELDA_INSIGHT_BOE') is not None) and (os.getenv('ZELDA_INSIGHT_BOE').strip() == '1')

def is_gray() -> bool:
    return (os.getenv('ZELDA_INSIGHT_GRAY') is not None) and (os.getenv('ZELDA_INSIGHT_GRAY').strip() == '1')

~~~
## 3.2 params
1. 引入environment
2. 根据environment中定义的方法定义变量
~~~python
from service.utils import environment

_PLOTLY_ONLINE_URL_BASED_TOS = f"https://data.bytedance.net/insight/api/file/?businessId=tea&fileName=plotly.min.js"
_PLOTLY_BOE_URL_BASED_TOS = "../../plotly.js"
PLOTLY_URL_BASED_TOS = _PLOTLY_ONLINE_URL_BASED_TOS if environment.is_online() else _PLOTLY_BOE_URL_BASED_TOS
