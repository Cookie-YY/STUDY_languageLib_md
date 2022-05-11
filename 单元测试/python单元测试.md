# 1. pytest
- 规范：`test_*.py` / `*_test.py` / `Test*` (类)
- 将所有测试都放到project/tests目录下
- pytest.ini路径较随意：
    - project/tests/pytest.ini
    - project/pytest.ini
- 在项目根目录执行 pytest tests
## 1.1 编写测试用例
~~~python
# 1. 参数化
def get_parmas():
    return [("1", "123", "1123"), ("2", "456", "2456")]
@pytest.mark.parametrize(
    "user,pw,expected",get_parmas(),
    ids=["case1", "case2"]
)
def test_login(user, pw, expected):
    assert user+pw == expected
# 参数化的叠加：参数的笛卡尔积
@pytest.mark.parametrize("arg1", [1,2], ids=["arg1=1", "arg1=2"])
@pytest.mark.parametrize("arg2", [3,4], ids=["arg2=3", "arg2=4"])
def test_dikaer(arg1, arg2):
    # 共调用4次

# 2. 标记
@pytest.mark.slow  # 需要在ini文件中注册 pytest -m slow tests执行
def test_hello():
    assert 1==1

# 3. 跳过
"可以直接修饰类，整个类都不执行"
"pytestmark = pytest.mark.skip() 文件中添加后，整个文件不执行"
# @pytest.mark.skip(reason="就是跳过")  # 无条件跳过
# @pytest.mark.skip  # 无条件跳过
# myskip = pytest.mark.skipif(condition=2>1)  @myskip装饰
@pytest.mark.skipif(condition=2>1, reason="就是跳过")
def test_hello():
    assert 1==1

# 4. 用例增加重试
@pytest.mark.flaky(returns=3,returns_delay=2)
def test_hello():
    assert 1==1
# 3. 生命周期（类外的函数）
setup_module(module)   # 一个文件
setup_function(func)
setup()
test_func()
teardown()
teardown_function(func)
teardown_module(module)

# 4. 生命周期（类内方法）
class TestMe:
    @classmethod
    def setup_class(cls):pass
    def setup_method(self, method):pass
    def setup(self, method):pass
    def teardown(self, method):pass
    def teardown_method(self, method):pass
    @classmethod
    def teardown_class(cls):pass

# 5. fixture表示依赖
@pytest.fixture()
def first_entry():
    return ("a", "b")

@pytest.fixture()
def second_entry():
    return "c"

def test_string(first_entry, second_entry):  # 因为引用了所以执行
    assert first_entry[0] == "a"
    assert first_entry[1] == "b"
    assert second_entry == "c"

@pytest.mark.usefixtures("second_entry")
@pytest.mark.usefixtures("first_entry")  # 不引用也可以执行
def test_ref():
    pass
# conftest.py 指定 项目级别的fixture
# 当前目录下以及子目录下的test文件自动获得 conftest.py中定义的fixture

# 6. monkeypatch
def test_load_settings_from_file(monkeypatch):
    monkeypatch.setenv('ENV_FOR_DYNACONF', 'pytest')
    settings.configure()

    assert settings.env == 'pytest'  # assert 一个布尔表达式
~~~
## 1.2 执行测试用例
### 1.2.1 命令行
~~~bash
# 根目录下执行，tests是一个package
# 会寻找tests这个package下所有符合条件的测试函数并执行
pytest tests
pytest -x tests  # 失败即退出
pytest -k config tests  # tests寻找包含config关键字的测试
pytest --maxfail=2 tests # 最多失败2个
pytest -n auto tests  # 多核运行  需要安装pytest-xdist  3
pytest -m slow tests  # 执行标记 需要在ini文件注册
pytest -m "not slow" tests  # 执行非标记
pytest --reruns 5 tests  # 失败重运行，需要安装pytest-rerunfailures
pytest --reruns 5 --reruns-delay 1 tests  # 失败重运行，需要安装pytest-rerunfailures
pytest --durations=10 -vv # 最慢的10个用例
# 报错时候的信息
--showlocals  -l --full-trace
--tb=auto long short line native no
pytest --pdb --maxfail=3  # 前三次失败进行调试
pytest --pdb -x  # 第一次失败就退出，并进入pdb
"""
p(输出)   pp(输出)    l 1,7(列出错误)   a(列出参数)
u(向上)   d(向下)     q(退出)
"""
~~~
### 1.2.2 python代码
1. 一般用这种方式执行自己py文件中的测试用例
~~~python
import pytest

if __name__ == '__main__':
    # 1. 执行所有测试用例
    pytest.main()
    # 2. 执行指定文件的指定测试
    pytest.main(["-s", "test_config.py::test_load_settings_from_env_var"])
~~~

## 1.3 配置文件
### 1.3.1 pytest.ini
1. 会在python代码文件所在目录或者 pytest执行的目录下搜索pytest.ini文件
~~~ini
[pytest]
disable_test_id_escaping_and_forfeit_all_rights_to_community_support=True  # 支持中文显示
addopts = -s -l -v --html=./report.html  # 可以直接pytest进行使用
testpaths = packagename1 ./packagename2  # 只搜索当前目录下的包
norecursedirs = test*  # test* package下的包就不搜索了
markers = 
    slow: marks tests as slow

python_files = auto*.py  # 修改搜索的行为
python_classes = Auto_*  # 修改搜索的行为
python_functions = auto_* # 
~~~

### 1.3.2 conftest.py
#### 1.3.2.1 fixture的全局定义
~~~python
@pytest.fixture()
def first_entry():  # conftest.py 所在目录及其子目录都可以用first_entry参数
    return ("a", "b")
~~~
#### 1.3.2.2 输出中文
~~~python
def pytest_collection_modifyitems(items):
    for item in items:
        item.name = item.name.encode("utf-8").decode("unicode_escape")
        print(item.nodeid)
        item._nodeid = item.nodeid.encode("utf-8").decode("unicode_escape")
~~~ 
## 1.4 mock与打桩
### 1.4.1 pytest_mock
~~~python
from pytest_mock import mocker
def test_mocker(mocker):
    mocker.patch("package.func", return_value=3)
    assert package.func() == 3  # 其他使用了这个函数的返回值都是3
~~~
### 1.4.2 mock
~~~python
# 方法1：装饰器
@mock.patch("package.func", return_value=3)
def test_mocker(mock_request):
    assert package.func() == mock_request.return_value  # 其他使用了这个函数的返回值都是3
# 方法2：with
def test_mocker():
    with mock.patch("package.func", side_effets=3) as mock_func:
        assert package.func() == mock_func.return_value  # 其他使用了这个函数的返回值都是3
~~~
### 1.4.3 monkeypatch
1. setattr
2. setenv
~~~python
# 1. mock函数
def test_setattr(monkeypatch):
    def mock_return(path): return 3
    with monkeypatch.context() as m:
        m.setattr(package, "func", mock_return)
        assert package.func() == 3

# 2. mock环境变量
def test_setenv(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    assert os.getenv("ENV") == "test"
~~~
### 1.4.4 数据库
~~~python
# 1. redis
from fakeredis import FakeStrictRedis
from rq import Queue

queue = Queue(is_async=False, connection=FakeStrictRedis())
job = queue.enqueue(my_long_running_job)
assert job.is_finished
~~~

## 1.5 报告生成
### 1.5.1 xml
pytest path.py::test_func  --junit-xml=./report/test.xml
### 1.5.2 在线
pytest path.py::test_func  --pastebin=all
### 1.5.3 html（常用）
pytest path.py::test_func  --html=./report.html  `需要安装pytest-html`
### 1.5.4 allure（酷炫、可以记录历史）
1. 安装jdk1.8
2. 解压allure压缩包
3. 配置allure的bin到环境变量path中
4. 安装 allure-pytest
5. pytest tests --alluredir ./result
    - pytest.main([])
6. allure generate ./result/ -o ./report_allure/ --clean
    - os.system()

# 1.6 jenkins集成
## 1.6.1 安装jenkins
1. 启动
    java -jar jenkins.war --httpPort=8081
2. 进入浏览器，输入用户名密码
3. New item，选择free style
4. 选择build中的shell，输入命令
5. 点击build now进行构建

### 1.7 常用插件
插件|说明|用法
—-|--|--
pytest-xdist | 多核支持 | `-n 3` or `-n auto`
pytest-html  | html报告支持 | `--html=./test.html`
pytest-rerunfailures  | 失败重运行 | `--reruns 5 --reruns-delay 1`
allure-pytest | allure报告支持 | `--alluredir ./result`
pytest_mock | mock数据 | `from pytest_mock import mocker`
