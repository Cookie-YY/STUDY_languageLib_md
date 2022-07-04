# 1. pip
~~~bash
# 指定源
python3 -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
# 指定源安装
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
~~~
# 2. poetry
- pyproject.toml: poetry init 工具生成
- poetry.lock: 通过 pyproject.toml 的依赖包生成
## 2.1 启动一个项目
~~~bash
# 1. 安装依赖，从poetry.lock安装
poetry install # 安装所有依赖
poetry install --no-dev  # 安装非dev的依赖（部署时使用）

# 2. 启动项目: poetry run 后面跟可以运行的命令
poetry run python main.py

# 3. 进入虚拟环境的shell中
poetry shell

### 如果是一个非poetry的项目
poetry init
cat requirements.txt | grep -E '^[^# ]' | cut -d= -f1 | xargs -n 1 poetry add
~~~
## 2.2 开发一个项目
~~~bash
# 1. 初始化项目：通过交互式问题得到pyproject.toml
poetry init
# 2. 安装依赖
poetry add flask=2.22.0
poetry add pytest --dev
# 3. 升级依赖：poetry lock 会重新计算依赖（相当于升级了所有依赖）
poetry update <package>
# 4. 查看依赖
poetry show --tree
poetry show --latest
# 5. 卸载依赖
poetry remove requests  # 会将依赖包一起卸载
# 6. 固化依赖：从 pyproject.toml 生成出 poetry.lock
poetry lock

# 虚拟环境管理
poetry env list --full-path

poetry config --list
poetry config virtualenvs.create false --local
poetry config virtualenvs.create --local --unset
# pycharm手动指定解释器：
# 如：E:\Documents\Library\virtualenvs\httprunner-ih9MoPBn-py3.7\Scripts\python.exe
~~~
![配置项](https://pic4.zhimg.com/80/v2-c4c25d5b87dad79bee7e707480b23013_1440w.jpg)
## 2.3 部署一个项目
- 一般导出requirements.txt 进行线上部署（速度快）
~~~bash
# 1. 生成 requirements.txt
poetry export -f requirements.txt -o requirements.txt --without-hashes

# 2. 线上安装
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
~~~
## 2.4 发布一个项目
~~~bash
# 公司内打源码包
poetry build -f sdist

# 公司外可以考虑打二进制包
poetry build -f wheel

# 推送上传
peotry publish --help
~~~
## 2.5 pyproject.toml示例
~~~toml
# 基础信息
[tool.poetry]
authors = ["Yao Fu <fuyao@stu.pku.edu.cn>"]
name = "Demo repo"
description = "Demo repo"
version = "0.1.1"

repository = ""  # 仓库链接
documentation = ""  # 文档链接
homepage = ""  # 主页链接
maintainers = [
  "Yao Fu <fuyao@stu.pku.edu.cn>",
  ...  # 其他人
]
readme = "README.md"


[tool.poetry.dependencies]
# 项目依赖放到这里
# See https://python-poetry.org/docs/dependency-specification/
# ^x.y.z preserve left most non-zero digit.
# ~x.y.z preserve x.y, ~x.y preserve x
absl-py = ">=0.12.0 <1.0"
protobuf = [
  {version = ">=3.18.0 <4.0", python = ">=3.6"},
  {version = "^3.18.0", python = "=3.5"},
  {version = "3.17.3", python = ">=2.7 <3"},
]
# 如果你想支持多 Python 版本，可以这样指定
python = "^2.7 || ^3.5"
six = "^1.16.0"

[tool.poetry.dev-dependencies]
# 开发工具放到这里
isort = [
  {version = "^5.8", python = "^3.6"},
  {version = "^4.3.21", python = "^2.7 || 3.5"},
]
pylint = [
  {version = "^2.6.2", python = "^3.5"},
  {version = "^1.9.5", python = "^2.7"},
]
toml = ">=0.10.2 <1.0"
yapf = ">=0.30 <1.0"

[[tool.poetry.source]]
# 指定使用其他 pypi 源（一般换成公司的）
default = true
name = "tsinghua"
url = "https://pypi.tuna.tsinghua.edu.cn/simple/"

[build-system]
build-backend = "poetry.core.masonry.api"
requires = ["poetry-core>=1.0.0"]

#
# 一些常见工具也支持从 pyproject.toml 读取配置
#

[tool.isort]
force_single_line = true
indent = "    "
line_length = 80
skip_glob = "**/*_pb2.py"

[tool.yapf]
based_on_style = "google"
column_limit = 80
split_before_named_assigns = true
~~~

# 2. pipenv
- Pipfile
- Pipfile.lock
~~~bash
######## 从requirements.txt创建虚拟环境并安装依赖 ########
pipenv install -r path/to/requirements.txt

# 创建虚拟环境
pipenv --python 3.7 

# 安装依赖
pipenv install flask==2.22.0 --skip-lock
pipenv install --skip-lock -i https://pypi.tuna.tsinghua.edu.cn/simple -v
# 进入虚拟环境
pipenv shell

# 以虚拟环境执行脚本
pipenv run python run_service.py 
~~~
