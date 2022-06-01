# 1. 时间字符串解析
1. 数字解析成秒数
2. 支持 "1m" "1d" "1s"表示
~~~python
def parse_timeout(timeout):
    """Transfer all kinds of timeout format to an integer representing seconds"""
    if not isinstance(timeout, numbers.Integral) and timeout is not None:
        try:
            timeout = int(timeout)
        except ValueError:
            digit, unit = timeout[:-1], (timeout[-1:]).lower()
            unit_second = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
            try:
                timeout = int(digit) * unit_second[unit]
            except (ValueError, KeyError):
                raise TimeoutFormatError('Timeout must be an integer or a string representing an integer, or '
                                         'a string with format: digits + unit, unit can be "d", "h", "m", "s", '
                                         'such as "1h", "23m".')

    return timeout
~~~
# 2. 可调用类型整理
~~~python
# Set the core job tuple properties
job._instance = None
if inspect.ismethod(func):
    job._instance = func.__self__
    job._func_name = func.__name__
elif inspect.isfunction(func) or inspect.isbuiltin(func):
    job._func_name = '{0}.{1}'.format(func.__module__, func.__qualname__)
elif isinstance(func, string_types):
    job._func_name = as_text(func)
elif not inspect.isclass(func) and hasattr(func, '__call__'):  # a callable class instance
    job._instance = func
    job._func_name = '__call__'
else:
    raise TypeError('Expected a callable or a string, but got: {0}'.format(func))
job._args = args
job._kwargs = kwargs
~~~
# 3. 字符串调用
## 3.1 默认与覆盖：字符串调用
~~~python
def backend_class(holder, default_name, override=None):
    """Get a backend class using its default attribute name or an override"""
    if override is None:
        return getattr(holder, default_name)
    elif isinstance(override, string_types):
        return import_attribute(override)
    else:
        return override

~~~
## 3.2 字符串和绑定：函数解析成字符串再动态导入
~~~python
# 1. 可调用的检查
if not inspect.isfunction(on_success) and not inspect.isbuiltin(on_success):
    raise ValueError('on_success callback must be a function')
job._success_callback_name = '{0}.{1}'.format(on_success.__module__, on_success.__qualname__)

# 2. 绑定成一个属性
@property
def success_callback(self):
    if self._success_callback is UNEVALUATED:
        if self._success_callback_name:
            self._success_callback = import_attribute(self._success_callback_name)
        else:
            self._success_callback = None

    return self._success_callback

# 3. 载入并执行
def run_sync(self, job):
    try:
        job = self.run_job(job)
    except:  # noqa
        job.set_status(JobStatus.FAILED)
        if job.failure_callback:
            job.failure_callback(job, self.connection, *sys.exc_info())
    else:
        if job.success_callback:
            job.success_callback(job, self.connection, job.result)

    return job

# 附录：字符串的导入
def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    name_bits = name.split('.')
    module_name_bits, attribute_bits = name_bits[:-1], [name_bits[-1]]
    module = None
    # When the attribute we look for is a staticmethod, module name in its
    # dotted path is not the last-before-end word
    # E.g.: package_a.package_b.module_a.ClassA.my_static_method
    # Thus we remove the bits from the end of the name until we can import it
    #
    # Sometimes the failure during importing is due to a genuine coding error in the imported module
    # In this case, the exception is logged as a warning for ease of debugging.
    # The above logic will apply anyways regardless of the cause of the import error.
    while len(module_name_bits):
        try:
            module_name = '.'.join(module_name_bits)
            module = importlib.import_module(module_name)
            break
        except ImportError:
            logging.warning("Import error for '%s'" % module_name, exc_info=True)
            attribute_bits.insert(0, module_name_bits.pop())

    if module is None:
        raise ValueError('Invalid attribute name: %s' % name)

    attribute_name = '.'.join(attribute_bits)
    if hasattr(module, attribute_name):
        return getattr(module, attribute_name)

    # staticmethods
    attribute_name = attribute_bits.pop()
    attribute_owner_name = '.'.join(attribute_bits)
    attribute_owner = getattr(module, attribute_owner_name)

    if not hasattr(attribute_owner, attribute_name):
        raise ValueError('Invalid attribute name: %s' % name)

    return getattr(attribute_owner, attribute_name)
~~~
# 4. local变量
单独写成了local.py文件，[解读参考](https://selfboot.cn/2016/08/26/threadlocal_implement/)

1. 本质是一个全局变量（字典）通过线程或协程的__ident_id__区分
2. 使得不用每次都传一堆参数
## 4.1 应用
1. flask中通过local对象保存请求信息，开始时入栈，结束后出栈
2. rq中保存connection（具体见5）
# 5. 装饰器
**定义**
- finally的内容就是__exit__的内容

**使用**
- **不管类还是函数加装饰器，都是一种特殊的实例化调用**
- 方法1. yield something，被as接收
- 方法2. yield 空，可以让函数通过 本地栈的方式获取参数
- 类装饰器 as 接收 __enter__的返回值（一般是self）
~~~python
@contextmanager
def Connection(connection=None):  # noqa
    if connection is None:
        connection = Redis()
    push_connection(connection)
    try:
        yield
    finally:
        popped = pop_connection()
        assert popped == connection, \
            'Unexpected Redis connection was popped off the stack. ' \
            'Check your Redis connection setup.'


def push_connection(redis):
    """Pushes the given connection on the stack."""
    _connection_stack.push(redis)


def pop_connection():
    """Pops the topmost connection from the stack."""
    return _connection_stack.pop()

# 清空并放进去一个connection
def use_connection(redis=None):
    """Clears the stack and uses the given connection.  Protects against mixed
    use of use_connection() and stacked connection contexts.
    """
    assert len(_connection_stack) <= 1, \
        'You should not mix Connection contexts with use_connection()'
    release_local(_connection_stack)

    if redis is None:
        redis = Redis()
    push_connection(redis)

# 返回栈顶的
def get_current_connection():
    """Returns the current Redis connection (i.e. the topmost on the
    connection stack).
    """
    return _connection_stack.top

# 传了就用你的connection，没传就用栈顶的
def resolve_connection(connection=None):
    """Convenience function to resolve the given or the current connection.
    Raises an exception if it cannot resolve a connection now.
    """
    if connection is not None:
        return connection

    connection = get_current_connection()
    if connection is None:
        raise NoRedisConnectionException('Could not resolve a Redis connection')
    return connection

from local import LocalStack  # 就是整理出来的local.py文件
_connection_stack = LocalStack()

__all__ = ['Connection', 'get_current_connection', 'push_connection',
           'pop_connection', 'use_connection']

~~~
# 6. 彩色日志
~~~python
class _Colorizer:
    def __init__(self):
        esc = "\x1b["

        self.codes = {}
        self.codes[""] = ""
        self.codes["reset"] = esc + "39;49;00m"

        self.codes["bold"] = esc + "01m"
        self.codes["faint"] = esc + "02m"
        self.codes["standout"] = esc + "03m"
        self.codes["underline"] = esc + "04m"
        self.codes["blink"] = esc + "05m"
        self.codes["overline"] = esc + "06m"

        dark_colors = ["black", "darkred", "darkgreen", "brown", "darkblue",
                       "purple", "teal", "lightgray"]
        light_colors = ["darkgray", "red", "green", "yellow", "blue",
                        "fuchsia", "turquoise", "white"]

        x = 30
        for d, l in zip(dark_colors, light_colors):
            self.codes[d] = esc + "%im" % x
            self.codes[l] = esc + "%i;01m" % x
            x += 1

        del d, l, x

        self.codes["darkteal"] = self.codes["turquoise"]
        self.codes["darkyellow"] = self.codes["brown"]
        self.codes["fuscia"] = self.codes["fuchsia"]
        self.codes["white"] = self.codes["bold"]

        if hasattr(sys.stdout, "isatty"):
            self.notty = not sys.stdout.isatty()
        else:
            self.notty = True

    def reset_color(self):
        return self.codes["reset"]

    def colorize(self, color_key, text):
        if self.notty:
            return text
        else:
            return self.codes[color_key] + text + self.codes["reset"]


colorizer = _Colorizer()


def make_colorizer(color):
    """Creates a function that colorizes text with the given color.

    For example:

        green = make_colorizer('darkgreen')
        red = make_colorizer('red')

    Then, you can use:

        print "It's either " + green('OK') + ' or ' + red('Oops')
    """
    def inner(text):
        return colorizer.colorize(color, text)
    return inner

green = make_colorizer('darkgreen')
yellow = make_colorizer('darkyellow')
blue = make_colorizer('darkblue')

logger.info('*** Listening on %s...', green(', '.join(qnames)))
~~~
# 7. 信号
~~~python
def request_force_stop(self, signum, frame):
    """Terminates the application (cold shutdown).
    """
    self.log.warning('Cold shut down')

    # Take down the horse with the worker
    if self.horse_pid:
        self.log.debug('Taking down horse %s with me', self.horse_pid)
        self.kill_horse()
        self.wait_for_horse()
    raise SystemExit()

def request_stop(self, signum, frame):
    """Stops the current worker loop but waits for child processes to
    end gracefully (warm shutdown).
    """
    self.log.debug('Got signal %s', signal_name(signum))

    signal.signal(signal.SIGINT, self.request_force_stop)
    signal.signal(signal.SIGTERM, self.request_force_stop)

    self.handle_warm_shutdown_request()
    self._shutdown()

def _shutdown(self):
    """
    If shutdown is requested in the middle of a job, wait until
    finish before shutting down and save the request in redis
    """
    if self.get_state() == WorkerStatus.BUSY:
        self._stop_requested = True  # 这里用了一个变量记录是否关闭
        self.set_shutdown_requested_date()
        self.log.debug('Stopping after current horse is finished. '
                        'Press Ctrl+C again for a cold shutdown.')
        if self.scheduler:
            self.stop_scheduler()
    else:
        if self.scheduler:
            self.stop_scheduler()
        raise StopRequested()
~~~

# 8. 命令行工具
1. 更多用法参考：cli命令行.py
~~~python
blue = make_colorizer('darkblue')


# Disable the warning that Click displays (as of Click version 5.0) when users
# use unicode_literals in Python 2.
# See http://click.pocoo.org/dev/python3/#unicode-literals for more details.
click.disable_unicode_literals_warning = True

@main.command()
@click.option('--interval', '-i', type=float, help='Updates stats every N seconds (default: don\'t poll)')
@click.option('--raw', '-r', is_flag=True, help='Print only the raw numbers, no bar charts')
@click.option('--only-queues', '-Q', is_flag=True, help='Show only queue info')
@click.option('--only-workers', '-W', is_flag=True, help='Show only worker info')
@click.option('--by-queue', '-R', is_flag=True, help='Shows workers by queue')
@click.argument('queues', nargs=-1)
@pass_cli_config
def info(cli_config, interval, raw, only_queues, only_workers, by_queue, queues,
         **options):
    """RQ command-line monitor."""

    if only_queues:
        func = show_queues
    elif only_workers:
        func = show_workers
    else:
        func = show_both

    try:
        with Connection(cli_config.connection):

            if queues:
                qs = list(map(cli_config.queue_class, queues))
            else:
                qs = cli_config.queue_class.all()

            for queue in qs:
                clean_registries(queue)
                clean_worker_registry(queue)

            refresh(interval, func, qs, raw, by_queue,
                    cli_config.queue_class, cli_config.worker_class)
    except ConnectionError as e:
        click.echo(e)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo()
        sys.exit(0)
~~~
# 9. Thread
~~~python
class PubSubWorkerThread(threading.Thread):
    def __init__(self, pubsub, sleep_time, daemon=False):
        super(PubSubWorkerThread, self).__init__()
        self.daemon = daemon
        self.pubsub = pubsub
        self.sleep_time = sleep_time
        self._running = threading.Event()  # 用一个变量记录running状态

    def run(self):
        if self._running.is_set():
            return
        self._running.set()
        pubsub = self.pubsub
        sleep_time = self.sleep_time
        while self._running.is_set():
            pubsub.get_message(ignore_subscribe_messages=True,
                               timeout=sleep_time)
        pubsub.close()

    def stop(self):
        # trip the flag so the run loop exits. the run loop will
        # close the pubsub connection, which disconnects the socket
        # and returns the connection to the pool.
        self._running.clear()
~~~