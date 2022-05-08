# 1. concurrent.futures 并发
1. 优点：通过高层抽象进程和线程对象
2. 优点：统一处理future
    - 使用执行器的map方法，要求顺序
    - 使用模块的as_completed方法，方法没有顺序
3. 缺点：
    - 所有的timeout只代表父进程异常：正在运行的future无法被取消
    - 其他同步的方法需要借助其他模块实现
## 1.1 executor类
1. 对线程和进程提供的抽象
    - concurrent.futures.{ThreadPoolExecutor, ProcessPoolExecutor}
### 1.1.1 map()返回迭代器
1. 顺序：迭代器的顺序和提交任务的顺序一致，不管任务的耗时排序如何
2. 异常：
    - 子任务出现异常，在迭代器拿到相应内容时抛出
    - 第一次失败时，后面的任务不会继续进行
3. timeout：有一个timeout参数
    - 如果timeout时间到了，`__next__()`拿不到东西，会抛出异常
    - 时间到了会尝试调用所有future的cancel方法（没开始的会取消，开始的不会有反应）
4. with用法
    - 在__exit__时调用了shutdown(wait=True)方法
5. map返回的迭代器的结果是`[future.result()]`
~~~python
import concurrent.futures.ProcessPoolExecutor as pool

with pool() as executor:
    # 要求顺序
    results = executor.map(is_even, [0,1,2,3,4,5,6,7])

while True:
    try:
        result = results.__next__()
    except StopIteration:
        break
    except ZeroDivisionError as e:
        print(e.__repr__())
~~~
### 1.1.2 submit()一次运行
~~~python
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    future1 = executor.submit(f, 0)
    future2 = executor.submit(f, 10)
    future3 = executor.submit(f, 20)
todos = [future1, future2, future3]
# 不要求顺序
for future in concurrent.futures.as_completed(todos):
    try:
        print(future.result())
    except ZeroDivisionError as e:
        print(e.__repr__())
~~~

### 1.1.3 shutdown(wait=True)释放资源
1. 如果 wait 为 True，那么这个方法会在所有等待的 future 都执行完毕，并且属于执行器 executor 的资源都释放完之后才会返回
2. 如果 wait 为 False，本方法会立即返回。属于执行器的资源会在所有等待的 future 执行完毕之后释放
3. 不管 wait 取值如何，整个 Python 程序在等待的 future 执行完毕之前不会退出
4. with 语句会用 wait=True 的默认参数调用 Executor.shutdown() 方法

## 1.2 future类
### 1.2.1 状态判断
- running() 判断：是否正在运行
- done() 判断：是否已完成（正常完成或被取消）
- cancelled() 判断：是否是取消状态
### 1.2.2 其他
- cancel() 取消任务。进行中的无法取消
- result(timeout=None) 返回调用的返回值
- exception(timeout=None) 返回调用的异常
    - 超时：concurrent.futures.TimeoutError
    - 取消：concurrent.futures.CancelledError
    - 没有异常：None
- add_done_callback(fn) 按照添加顺序执行
    - 需要判断状态
    - future会作为参数传给fn
## 1.3 模块方法
### 1.3.1 as_completed
~~~python
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Executor, as_completed

start = time.time()
with ProcessPoolExecutor(max_workers=2) as pool:
    futures = [ pool.submit(gcd, pair) for pair in numbers]
    for future in futures:
        print '执行中:%s, 已完成:%s' % (future.running(), future.done())
    print '#### 分界线 ####'
    for future in as_completed(futures, timeout=2):
        print '执行中:%s, 已完成:%s' % (future.running(), future.done())
end = time.time()
print 'Took %.3f seconds.' % (end - start)
~~~
### 1.3.2 wait
1. wait(concurrent.futures.ALL_COMPLETED)  == as_completed
2. wait(concurrent.futures.FIRST_COMPLETED) 得到第一个完成的任务
~~~python
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Executor, as_completed, wait, ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION

start = time.time()
with ProcessPoolExecutor(max_workers=2) as pool:
    futures = [ pool.submit(gcd, pair) for pair in numbers]
    for future in futures:
        print '执行中:%s, 已完成:%s' % (future.running(), future.done())
    print '#### 分界线 ####'
    done, unfinished = wait(futures, timeout=2, return_when=ALL_COMPLETED)
    for d in done:
        print '执行中:%s, 已完成:%s' % (d.running(), d.done())
        print d.result()
end = time.time()
print 'Took %.3f seconds.' % (end - start)
~~~
# 2. multiprocessing
1. 优点：
    - 支持取消terminate语义
    - multiprocessing提供 Queue、Pipe、Lock语义
2. 缺点：
    概念和相关包较多，组织混乱，
        很多同步原语：Barrier、BoundedSemaphore、Condition、Event、Lock在管理器和模块中都有相关方法且都是从threading库中来的
* 注意 daemon的进程无法创建子进程：进程池中的进程默认daemon
## 2.1 进程池
pool实例化时可以指定 initializer
### 2.1.1 apply系列
1. apply(func, args)
2. apply_async(func, args, callback, error_callback)
### 2.1.2 map系列
1. starmap(func, [(1,2), (3, 4)])  ->  func(1,2)  func(3,4)
2. imap_unordered
3. map_async: 类似apply_async
4. starmap_async
### 2.1.3 进程池管理
1. close(): 阻止后续任务提交到进程池，当所有任务执行完成后，工作进程会退出。
2. terminate(): 会杀死进行中任务
    - 不必等待未完成的任务，立即停止工作进程
    - 当进程池对象被垃圾回收时，会立即调用 terminate()
    - with的退出会调用 terminate
3. join(): 等待工作进程结束。调用 join() 前必须先调用 close() 或者 terminate()
4. get(timeout)/wait(timeout)
    - get()获取结果
    - wait()阻塞直到返回
5. ready()/successful() 状态判断
~~~python
from multiprocessing import Pool
import time

def f(x):
    return x*x

if __name__ == '__main__':
    with Pool(processes=4, initializer=, initargs=) as pool:         # start 4 worker processes
        multiple_results = [pool.apply_async(os.getpid, ()) for i in range(4)]
        print([res.get(timeout=1) for res in multiple_results])


        print(pool.map(f, range(10)))       # prints "[0, 1, 4,..., 81]"

        it = pool.imap(f, range(10))
        print(next(it))                     # prints "0"
        print(next(it))                     # prints "1"
        print(it.next(timeout=1))           # prints "4" unless your computer is *very* slow

        result = pool.apply_async(time.sleep, (10,))
        print(result.get(timeout=1))        # raises multiprocessing.TimeoutError
~~~
## 2.2 类实例化进程
- start()
- join(): 一个进程可以被 join 多次
    - 尝试在启动进程之前join进程是错误的
    - 进程无法join自身，因为这会导致死锁
- terminate(): Unix使用 SIGTERM, Windows上使用 TerminateProcess()
    - 不会执行退出处理程序和finally子句
    - 进程的后代进程将不会被终止，变成孤儿进程
    - 可能会破坏其他共享结构
- kill(): 在Unix上使用 SIGKILL 信号
- close(): 释放所有资源
    - 如果底层进程仍在运行，则会引发 ValueError
- daemon: 默认为False
    - 设置为True: 进程无法创建子进程
    - 设置为True: 父进程退出后，一并杀死设置为True的进程
- name: 没有特殊含义，可以取个名字
- pid
- exitcode
    - exitcode == 0: 正常退出
    - exitcode == 1: 不是run()方法的报错而终止 
    - exitcode == 其他正数: sys.exit(N)
    - -N: 被 kill 信号杀死，信号值是N

### 2.2.1 直接实例化
~~~python
from multiprocessing import Process
import os

def f():
    print('func parent process:', os.getppid())
    print('func process id:', os.getpid())

if __name__ == '__main__':
    print('main parent process:', os.getppid())
    print('main process id:', os.getpid())
    p = Process(target=f, args=())
    p.start()
    p.join()
~~~
## 2.2.2 继承子类实例化
~~~python
class TaskProcess(multiprocessing.Process):
    def run(self):  # p.start会调用
        signal.signal(signal.SIGTERM, self.graceful_exit)
        pass
    def graceful_exit(self, signum, frame):
        self.current_process = psutil.Process()  # 当前进程
        self.subprocs = set([p.pid for p in self.current_process.children(recursive=True)])
        for child_id in self.subprocs:
            os.kill(child_id, signal.SIGKILL)
~~~
## 2.3 同步原语
1. 信号量就是个计数器，acquire()内置计数器-1，release()计数器+1
2. 初始信号量为1就是锁
3. RLock是递归锁，是python中的可重入锁：类似一个初始为零的信号量
4. daemon: 跟我一起死，发送的是SIGTERM信号
    - 无论是进程还是线程，都遵循：守护xxx会等待主xxx运行完毕后被销毁
    - 进程必须保证非守护线程都运行完毕后才能结束(否则会产生僵尸进程)
    - 主线程在其他非守护线程运行完毕后才算运行完毕（守护线程在此时就被回收）
5. join与JoinableQueue: 等你运行完
6. 条件变量: 一边的动作可以通知另一边
    - wait_for等待，notify唤醒
    - 基于锁，传入或者自动生成一个RLock
7. 事件: 调用 wait() 方法将进入阻塞直到标识为true
8. barrier: wait()方法保证后面的内容齐头并进

### 2.3.1 队列
#### 2.3.1.1 普通队列 Queue
1. multiprocessing提供一个Queue对象，线程和进程安全
2. 使用时需要传递queue对象
- qsize()
- empty()
- full()
- put(block, timeout)
- put_nowait()
- get()
- get_nowait()
- close(): 当前进程将不会再往队列中放入对象。一旦所有缓冲区中的数据被写入管道之后，后台的线程会退出。这个方法在队列被gc回收时会自动调用
- join_thread(): 调用了 close() 方法之后可用。这会阻塞当前进程，直到后台线程退出，确保所有缓冲区中的数据都被写入管道中。
~~~python
from multiprocessing import Process, Queue

def f(q):
    q.put([42, None, 'hello'])

if __name__ == '__main__':
    q = Queue()
    p = Process(target=f, args=(q,))
    p.start()
    print(q.get())    # prints "[42, None, 'hello']"
    p.join()
~~~
#### 2.3.1.2 简单队列 SimpleQueue
- 只有 empty()，get()，put(item)
- close()方法3.9新增
    - 关闭队列：释放内部资源。
    - 队列在被关闭后就不可再被使用。 例如不可再调用 get(), put() 和 empty() 等方法
#### 2.3.1.3 join队列 JoinableQueue
- 类似go的waitGroup
    - q.put() / q.get()
    - q.task_done()
    - q.join()
~~~python
def consumer(q):
    while True:
        res=q.get()
        if res is None:
            break
        time.sleep(random.randint(1,3))
        q.task_done()

def producer(q):
    for i in range(5):
        time.sleep(random.randint(1,2))
        q.put(str(i))


if __name__ == '__main__':
    # 1、共享的盆
    q=JoinableQueue()
    
    # 2、生产者们
    p1=Process(target=producer,args=(q,))
    p2=Process(target=producer,args=(q,))
    # 3、消费者们
    c1=Process(target=consumer,args=(q))
    c2=Process(target=consumer,args=(q))
    c1.daemon=True
    c2.daemon=True

    p1.start()
    p2.start()

    c1.start()
    c2.start()

    # 确定生产者确确实实已经生产完毕
    p1.join()
    p2.join()
    p3.join()
    q.join()  # 直到 q的个数变成0

    print('主进程结束')

~~~
### 2.3.2 管道
1. multiprocessing提供一个Pipe对象
2. 返回管道的两端，两个线程或进程，不同同时读同一端，或者写同一端
~~~python
from multiprocessing import Process, Pipe

def f(conn):
    conn.send([42, None, 'hello'])
    conn.close()

if __name__ == '__main__':
    parent_conn, child_conn = Pipe()
    p = Process(target=f, args=(child_conn,))
    p.start()
    print(parent_conn.recv())   # prints "[42, None, 'hello']"
    p.join()
~~~
### 2.3.3 锁
1. multiprocessing提供一个Lock对象
2. 使用try: do() finally: l.release()完成go
的defer语义
3. 中途被kill不会执行finally释放锁（可能造成死锁）
4. l.acquire(block=True) 默认阻塞，block=False，在已锁住的时候返回False
5. RLock 递归锁：亲自释放 + 可重入
~~~python
from multiprocessing import Process, Lock

def f(l, i):
    l.acquire()
    try:
        print('hello world', i)
    finally:
        l.release()
    # # 或者使用with
    # with l:
    #     print('hello world', i)


if __name__ == '__main__':
    lock = Lock()

    for num in range(10):
        Process(target=f, args=(lock, num)).start()
~~~
### 2.3.4 barrier
~~~python
def test(synchronizer, serializer):
    name = multiprocessing.current_process().name
    synchronizer.wait()  # 通过barrier的wait方法实现同步
    now = time()
    with serializer:
        print("process %s ----> %s" % (name, datetime.fromtimestamp(now)))
synchronizer = Barrier(2)
serializer = Lock()
Process(name='p1', target=test, args=(synchronizer,serializer)).start()
Process(name='p2', target=test, args=(synchronizer,serializer)).start()
~~~
### 2.3.5 信号量
~~~python
# from multiprocessing import Semaphore

from threading import Thread,Semaphore,current_thread
import time,random

sm=Semaphore(5)

def go_wc():
    sm.acquire()
    print('%s 上厕所ing' %current_thread().getName())
    time.sleep(random.randint(1,3))
    sm.release()

if __name__ == '__main__':
    for i in range(23):
        t=Thread(target=go_wc)
        t.start()
~~~
### 2.3.6 条件变量
- acquire()
- release()
- wait(): 阻塞直到被唤醒
- wait_for(func) while True版本的wait
- notify(n=1)
- notify_all()
~~~python
# Consume an item
# coding=utf-8
import threading
import time

con = threading.Condition()

num = 0

# 生产者
class Producer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        # 锁定线程
        global num
        con.acquire()
        while True:
            print "开始添加！！！"
            num += 1
            print "火锅里面鱼丸个数：%s" % str(num)
            time.sleep(1)
            if num >= 5:
                print "火锅里面里面鱼丸数量已经到达5个，无法添加了！"
                # 唤醒等待的线程
                con.notify()  # 唤醒小伙伴开吃啦
                # 等待通知
                con.wait()
        # 释放锁
        con.release()

# 消费者
class Consumers(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        con.acquire()
        global num
        while True:
            print "开始吃啦！！！"
            num -= 1
            print "火锅里面剩余鱼丸数量：%s" %str(num)
            time.sleep(2)
            if num <= 0:
                print "锅底没货了，赶紧加鱼丸吧！"
                con.notify()  # 唤醒其它线程
                # 等待通知
                con.wait()
        con.release()

p = Producer()
c = Consumers()
p.start()
c.start()
~~~
### 2.3.7 事件
- is_set(): 是否置为True（创建时为False）
- set(): 置为True
- clear(): 置为False
- wait(): 阻塞直到返回true
### 2.3.8 共享内存
1.  'd' 表示双精度浮点数， 'i' 表示有符号整数
2. 共享对象是进程和线程安全的（Value和Array都有一个lock的参数）
    - lock参数默认为True，会有一个锁保证线程进程安全
    - lock也可以传递自己的锁
3. multiprocessing.sharedctypes 对于共享内存有更多的方法
~~~python
from multiprocessing import Process, Value, Array

def f(n, a):
    n.value = 3.1415927
    for i in range(len(a)):
        a[i] = -a[i]

if __name__ == '__main__':
    num = Value('d', 0.0)
    arr = Array('i', range(10))

    p = Process(target=f, args=(num, arr))
    p.start()
    p.join()

    print(num.value)
    print(arr[:])
~~~
### 2.3.9 服务进程对象: 更灵活的共享内存
1. 比共享内存更灵活：支持的内容更多，但比共享内存更慢
2. 通过manager.xx()得到注册的实例（参考自定义管理器）
    - manager.xx() 创建一个共享对象，返回其代理
    - list和dict可以嵌套，但是修改必须在代理上修改
3. 可通过网络由不同计算机上的进程共享
**普通用法**
~~~python
from multiprocessing import Process, Manager

def f(d, l):
    d[1] = '1'
    d['2'] = 2
    d[0.25] = None
    l.reverse()

if __name__ == '__main__':
    with Manager() as manager:
        d = manager.dict()
        l = manager.list(range(10))

        p = Process(target=f, args=(d, l))
        p.start()
        p.join()

        print(d)
        print(l)
~~~

**自定义管理器**
~~~python
from multiprocessing.managers import BaseManager

class MathsClass:
    def add(self, x, y):
        return x + y
    def mul(self, x, y):
        return x * y

class MyManager(BaseManager):
    pass

MyManager.register('Maths', MathsClass)

if __name__ == '__main__':
    with MyManager() as manager:
        maths = manager.Maths()
        print(maths.add(4, 3))         # prints 7
        print(maths.mul(7, 8))         # prints 56
~~~

**远程调用（通过网络传递manger）**
~~~python
## 服务端
from multiprocessing.managers import BaseManager
from queue import Queue
queue = Queue()
class QueueManager(BaseManager): pass
QueueManager.register('get_queue', callable=lambda:queue)
m = QueueManager(address=('', 50000), authkey=b'abracadabra')
s = m.get_server()
s.serve_forever()

## 客户端
from multiprocessing.managers import BaseManager
class QueueManager(BaseManager): pass
QueueManager.register('get_queue')
m = QueueManager(address=('foo.bar.org', 50000), authkey=b'abracadabra')
m.connect()
queue = m.get_queue()
queue.put('hello')
~~~
## 2.4 模块方法
### 2.4.1 mp.set_start_method('spawn')
- spawn: 继承部分资源  **win只有spawn**  python3.8及以后mac默认
    - 父进程会启动一个全新的 python 解释器进程。
    - 子进程将只继承那些运行进程对象的 run() 方法所必需的资源。
    - 使用此方法启动进程相比使用 fork 或 forkserver 要慢上许多。
- fork: 继承所有资源，可以直接打到二进制包中   **unix默认**  python3.8以前mac默认
    - 父进程的所有资源都由子进程继承
    - 安全分叉多线程进程是棘手的
    - 只存在于Unix。Unix中的默认值
- forkserver
    - 分叉服务器进程是单线程的，因此使用 os.fork() 是安全的。没有不必要的资源被继承

~~~python
if __name__ == '__main__':
    print('main parent process:', os.getppid())
    print('main process id:', os.getpid())
    mp.set_start_method('spawn')
    p = Process(target=f, args=())
    p.start()
    p.join()
~~~

### 2.4.2 get_context('spawn')
1. 使用 get_context() 以避免干扰库用户的选择
~~~python
ctx = mp.get_context('spawn')
p = ctx.Process(target=f, args=())
~~~

### 2.4.3 get_start_method()
~~~python
string = mp.get_start_method()
~~~

### 2.4.4 进程创建关系
~~~python
print([p.pid for p in mp.active_children()])  # 不支持递归
print(mp.parent_process().pid)  # python3.8 主进程的parent是None
print(mp.current_process().pid)
~~~

### 2.4.5 CPU利用
~~~python
# CPU总核心：等价于os.cpu_count()
print(mp.cpu_count())
# 部分unix系统可用
print(len(os.sched_getaffinity(0)))  # 可用CPU核心数
~~~

### 2.4.6 线程
multiprocessing.dummy 是 线程版的multiprocessing
multiprocessing.dummy.Pool() 是线程池

# 3. psutil: 进程信息库
## 3.1 系统信息
~~~python
# CPU统计
psutil.cpu_count() # CPU逻辑数量
4
psutil.cpu_count(logical=False) # CPU物理核心
2
psutil.cpu_times()
scputimes(user=10963.31, nice=0.0, system=5138.67, idle=356102.45)
for x in range(2):
    print(psutil.cpu_percent(interval=1, percpu=True))
[14.0, 4.0, 4.0, 4.0]
[12.0, 3.0, 4.0, 3.0]

# 内存统计
psutil.virtual_memory()
svmem(total=8589934592, available=2866520064, percent=66.6, used=7201386496, free=216178688, active=3342192640, inactive=2650341376, wired=1208852480)
psutil.swap_memory()
sswap(total=1073741824, used=150732800, free=923009024, percent=14.0, sin=10705981440, sout=40353792)
# 返回的是字节为单位的整数，可以看到，总内存大小是8589934592 = 8 GB，已用7201386496 = 6.7 GB，使用了66.6%。
# 而交换区大小是1073741824 = 1 GB。

# 磁盘信息
psutil.disk_partitions() # 磁盘分区信息
[sdiskpart(device='/dev/disk1', mountpoint='/', fstype='hfs', opts='rw,local,rootfs,dovolfs,journaled,multilabel')]
psutil.disk_usage('/') # 磁盘使用情况
sdiskusage(total=998982549504, used=390880133120, free=607840272384, percent=39.1)
psutil.disk_io_counters() # 磁盘IO
sdiskio(read_count=988513, write_count=274457, read_bytes=14856830464, write_bytes=17509420032, read_time=2228966, write_time=1618405)
# 可以看到，磁盘'/'的总容量是998982549504 = 930 GB，使用了39.1%。文件格式是HFS，opts中包含rw表示可读写，journaled表示支持日志。

# 所有进程
psutil.pids()
[3865, 3864, 3863, 3856, 3855, 3853, 3776, ..., 45, 44, 1, 0]
~~~
## 3.2 进程对象
~~~python
p = psutil.Process()  # 当前进程
p = psutil.Process(3776)  # 指定进程

p.name() # 进程名称
'python3.6'
p.exe() # 进程exe路径
'/Users/michael/anaconda3/bin/python3.6'
p.cwd() # 进程工作目录
'/Users/michael'
p.cmdline() # 进程启动的命令行
['python3']
p.ppid() # 父进程ID
3765
p.parent() # 父进程
<psutil.Process(pid=3765, name='bash') at 4503144040>
p.children(recursive=True) # 子进程列表 支持递归找所有子进程
[]
p.status() # 进程状态
p.username() # 进程用户名
'michael'
p.create_time() # 进程创建时间
1511052731.120333
p.terminal() # 进程终端
'/dev/ttys002'
p.cpu_times() # 进程使用的CPU时间
pcputimes(user=0.081150144, system=0.053269812, children_user=0.0, children_system=0.0)
p.memory_info() # 进程使用的内存
pmem(rss=8310784, vms=2481725440, pfaults=3207, pageins=18)
p.open_files() # 进程打开的文件
[]
p.connections() # 进程相关网络连接
[]
p.num_threads() # 进程的线程数量
1
p.threads() # 所有线程信息
[pthread(id=1, user_time=0.090318, system_time=0.062736)]
p.environ() # 进程环境变量
{'SHELL': '/bin/bash', 'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:...', 'PWD': '/Users/michael', 'LANG': 'zh_CN.UTF-8', ...}
p.terminate() # 结束进程
~~~

# 4. joblib: 科学计算友好的并行库
# 5. subprocess
# 6. mpi4py
# 7. celery：分布式任务管理
# 8. rq：基于redis的分布式队列
# 9. gevent: 协程
# 10. async: 协程

