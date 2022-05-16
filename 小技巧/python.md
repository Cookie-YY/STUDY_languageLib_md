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


