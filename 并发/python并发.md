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
# 2. multiprocessing：基础的进程并发库
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
## 8.1 队列与初始化
~~~python
from rq import Queue
q = Queue(connection=Redis())

# 队列实例
# 1. 队列中任务个数
print(len(q))
# 2. 所有任务的id
queued_job_ids = q.job_ids
# 3. 所有任务的实例
queued_jobs = q.jobs
# 4. 特定任务的实例
job = q.fetch_job('my_id')
# 5. 删除整个队列
q.delete(delete_jobs=True)
# 6. 获取位置
q.get_job_position(job)

~~~
初始化队列参数|说明
--| --
name | 队列名称，默认default
connection | redis链接实例
is_async | 等待执行，默认True，False时在同一个线程中立即执行作业
default_timeout | 默认 None
job_class| 默认None
serializer|可换成json rq.serializers.JSONSerializer，默认pickle

## 8.2 任务与入队
~~~python
# 任务入队
# 方法1: 简单放入
job = q.enqueue(length_of_url, 'https://www.twle.cn/')
# 方法2: 字符串作为调用函数
job = q.enqueue('my_package.my_module.my_func', 3, 4)
# 方法3: enqueue的底层enqueue_call
job = q.enqueue_call(func=length_of_url,
               args=('https://www.twle.cn',),
               timeout=30)
# 方法4: 装饰器
@job('low', connection=my_redis_conn, timeout=5)
def add(x, y):
    return x + y
job = add.delay(3, 4)
# 方法5：定时与调度
job = queue.enqueue_at(datetime(2019, 10, 8, 9, 15), say_hello)
job = queue.enqueue_in(timedelta(seconds=10), say_hello)
# 方法6：尝试
from rq import Retry
job = queue.enqueue(say_hello, retry=Retry(max=3))
job = queue.enqueue(say_hello, retry=Retry(max=3, interval=[10, 30, 60]))
# 方法7：redis的pipeline
with q.connection.pipeline() as pipe:
  jobs = q.enqueue_many(
    [
      Queue.prepare_data(count_words_at_url, 'http://nvie.com', job_id='my_job_id'),
      Queue.prepare_data(count_words_at_url, 'http://nvie.com', job_id='my_other_job_id'),
    ]
    pipeline=pipe
  )
  pipe.execute()
# 方法8：创建再执行
from rq.job import Job
job = Job.create(count_words_at_url, 'http://nvie.com')
q.enqueue_job(job)

# 方法9：命令行
"""
rq enqueue path.to.func abc
rq enqueue path.to.func abc=def
"""
# 设置回调：60s的执行限制
def report_success(job, connection, result, *args, **kwargs):
    pass
def report_failure(job, connection, type, value, traceback):
    pass

# 任务实例
# 1. 获取任务实例
from rq.job import Job
job = Job.fetch('my_job_id', connection=redis)
# 2. 获取多任务实例
jobs = Job.fetch_many(['foo_id', 'bar_id'], connection=redis)
for job in jobs:
    print('Job %s: %s' % (job.id, job.func_name))
# 3. 获取结果
print(job.result) # 未完成时返回 None，完成时返回任务的返回值
# 4. 干掉job：正在running
from rq.command import send_stop_job_command
# This will raise an exception if job is invalid or not currently executing
send_stop_job_command(redis, job_id)
# 5. 取消job：还没running
from rq.registry import CanceledJobRegistry
job.cancel()
print(job.get_status())  # CANCELED
registry = CanceledJobRegistry(queue=job.origin, connection=job.connection)
print(job in registry)  # Job is in CanceledJobRegistry
# 6. 失败任务查询与调度
registry = FailedJobRegistry(queue=q)
registry = q.failed_job_registry
for job_id in registry.get_job_ids():
    # job = Job.fetch(job_id, connection=redis)
    registry.requeue(job_id)  # Puts back in its original queue
assert len(registry) == 0
# 7. 额外保存信息
job.meta['handled_by'] = socket.gethostname()
job.save_meta()
# 7. 命令行调度
# myqueue中执行的任务中失败的
rq requeue --queue myqueue -u redis://localhost:6379 foo_job_id bar_job_id
rq requeue --queue myqueue -u redis://localhost:6379 --all


# job示例方法
job.get_status(refresh=True)
job.get_meta(refresh=True)
job.origin # 任务的队列名称
job.func_name
job.args
job.kwargs
job.result
job.enqueued_at
job.started_at
job.ended_at
job.exc_info  # 异常信息
job.last_heartbeat
job.worker_name
job.refresh()
job.get_position()
~~~
enqueue参数 | 说明
-- | --
job_timeout|最大运行时间，默认300  支持字符串表示 '1h'，'3m'，'5s'
result_ttl|结果保存的时间 默认 500
ttl|队列中排队的最长时间，超过会被取消。如果指定值 -1，则表示不限时间
failure_ttl|失败任务保存时间，默认1年
depends_on|任务依赖，任务实例或任务id，支持列表
job_id|用于手动指定该作业任务的 id job_id
at_front|用于将该作业任务放置在队列的头部，而不是尾部，也就是说可以优先被执行
on_success|成功的回调
on_failure|失败的回调
## 8.3 worker与启动
- 如果想要并发执行，需要启动多个worker任务
- 每一个worker都会fork子进程来处理任务：fetch-fork-execute循环
### 8.3.1 命令行
1. 可以自定义worker class
    - -w 'path.to.GeventWorker'
2. 可以自定义job class
    - --job-class 'custom.JobClass'
3. 可以自定义queue class
    - --queue-class 'custom.QueueClass'
4. 可以指定异常处理
    - --exception-handler 'path.to.my.ErrorHandler'
~~~bash
rq worker  # 是一个常驻进程
rq worker high default low # 指定队列名
rq worker --with-scheduler
~~~
参数|说明
--|--
-b, --burst|使用临时模式，当处理完所有任务后自动退出
--logging_level TEXT|设置日志级别
-n, --name TEXT|用于指定工作进程的名称
--results-ttl INTEGER|用于指定作业任务执行结果的保存时间
--worker-ttl INTEGER|用于指定作业任务的最大执行时间
--job-monitoring-interval INTEGER|设置作业任务监控心跳时间
-v, --verbose|输出更多启动信息
-q, --quiet|输出更少启动信息
--sentry-dsn TEXT|将异常发送到该 Sentry DSN 上
--exception-handler TEXT|当异常发生时的异常处理器
--pid TEXT|将当前进程的编号写入指定的文件
-P, --path TEXT|指定模块导入路径
--connection-class TEXT|自定义指定连接 Redis 时使用的连接类
--queue-class TEXT|自定义 RQ Queue 类
-j, --job-class TEXT|自定义 RQ Job 类
-w, --worker-class TEXT|自定义 RQ Worker 类
-c, --config TEXT|RQ 配置信息的模块
-u, --url TEXT|用于指定 Redis 服务的连接信息
--serializer | rq.serializers.JSONSerializer
--help|输出帮助信息
#### 8.3.1.1 文件参数
- rq worker -c settings 进行启动
~~~python
REDIS_URL = 'redis://localhost:6379/1'

# You can also specify the Redis DB to use
# REDIS_HOST = 'redis.example.com'
# REDIS_PORT = 6380
# REDIS_DB = 3
# REDIS_PASSWORD = 'very secret'

# Queues to listen on
QUEUES = ['high', 'default', 'low']

# If you're using Sentry to collect your runtime exceptions, you can use this
# to configure RQ for it in a single step
# The 'sync+' prefix is required for raven: https://github.com/nvie/rq/issues/350#issuecomment-43592410
SENTRY_DSN = 'sync+http://public:secret@example.com/1'

# If you want custom worker name
# NAME = 'worker-1024'
~~~
### 8.3.2 python启动
~~~python
def my_handler(job, exc_type, exc_value, traceback):
    # return False: 不允许链式调用
    # return True or no return，允许链式调用
    pass  

from rq import Worker
queue = Queue('queue_name')
worker = Worker(
    [q], 
    connection=redis_client.client, 
    name='foo',
    exception_handlers=[foo_handler],
    disable_default_exception_handler=False
)
worker.work(
    with_scheduler=True,  # 支持调度
    burst=True  # 队列为空就退出（用于测试）
)
~~~
### 8.4 worker监控与控制
~~~python
workers = Worker.all(connection=redis)
workers = Worker.all(queue=queue)

for worker in workers:
    # 1. 杀死整个worker
    send_shutdown_command(redis, worker.name)
    # 2. 杀死当前任务
    if worker.state == WorkerStatus.BUSY:
        send_kill_horse_command(redis, worker.name)

# 整体监控
# pip install rq-dashboard
rq info
rq info high default
rq info -R
rq info --interval 1

~~~
worker属性|解释
--|--
hostname|主机名
pid|进程号
queues|监听的队列
state|suspended, started, busy, idle
current_job|正在运行的job
last_heartbeat|最后一次此worker被看见
birth_date|进程初始化时间
successful_job_count|worker完成了几个任务
failed_job_count|worker失败了了几个任务
total_working_time|总任务执行时长，单位秒

# 8.5 自定义类
## 8.5.1 自定义worker
- Subclasses of Worker which override handle_job_failure() should likewise take care to handle jobs with a stopped status appropriately.
## 8.6 存储
### 8.6.1 任务存储
键|类型|值
--|--|--
rq:queues | set | 具体任务队列：rq:queue:default
rq:queue:default | set | 排队的任务列表：任务id1、任务id2
rq:job:{任务id} | hash | 任务描述信息，**详见8.1.2**

### 8.6.2 任务描述（rq:job:{任务id}）
键|说明|值
--|--|--
timeout|任务执行的超时时间|180 **超时后该key被删**
origin|保存的作业任务队列|default
description|描述|一般是该作业任务的 __repr__ 函数结果: modelserver.job.sleep(10)
status|状态|queued、started、finished、failed、deferred
data|作业任务要执行的函数，pickle 序列化后的结果|\BeJxrYJmqzAABGj2iufkpqTnFqUVlqUV6WflJesU5qakFU/y8uVqn1E4pmaIHACZCDvU=
created_at|创建时间|2022-05-09T21:05:09.167316Z
enqueued_at|加入队列时间|2022-05-09T21:05:09.168197Z
started_at|开始时间|2022-05-09T21:05:09.214252Z
ended_at |结束时间| 2022-05-09T21:05:19.230443Z
last_heartbeat|最后心跳时间|2022-05-09T21:05:09.198273Z
success_callback_name
failure_callback_name
worker_name
result|返回的结果|\BgARLZC4=

### 8.6.3 任务执行
键|类型|值
--|--|--
rq:finished:default | SortedSet | 完成的任务id，时间戳
rq:workers:default|set| rq:worker:{worker id}
rq:workers|set|rq:worker:{worker id}
rq:queue:default | set | 排队的任务列表：任务id1、任务id2
rq:worker:{worker id} | hash | worker描述信息，**详见8.1.4**
### 8.6.4 worker 描述（rq:worker:{worker id}）
键|值
--|--
total_working_time|20.007605
current_job_working_time|0
ipaddress|127.0.0.1:50945
hostname|CO2DX6PZMD6R
version|1.10.1
state|idle
pid|56640
python_version|3.7.3|(v3.7.3:ef4ec6ed12,|Mar|25|2019,|16:52:21)|Inl...
queues|default
last_heartbeat|2022-05-09T20:52:24.678480Z
successful_job_count|2
birth|2022-05-09T20:38:34.517994Z

## 8.7 worker生命周期
1. 启动，加载 Python 环境
2. 出生登记。工作进程将自己注册到系统
3. 开始监听，从给定的队列中弹出作业任务并执行，如果没有作业任务且使用了临时模式，那么该工作进程将自动退出，否则会一直等待新的作业任务到来
4. 作业任务执行前准备。此时，工作进程会将自己的状态设定为 busy 并在 StartedJobRegistry 中注册作业任务来告诉系统它将开始工作
5. **fork 出一个子进程**。子进程将在失败安全 ( fail-safe ) 的上下文中执行真正的作业任务
6. 执行作业任务，这个一般由 fork 出的子进程来实行
7. 清理作业任务执行环境。 工作进程会将自己的状态设置为 idle 并将子进程执行的作业结果保存到 Redis 中并设置结果的过期时间为 result_ttl。 作业任务也从 StartedJobRegistry 中删除，并在成功执行时添加到 FinishedJobRegistry，或者在失败的情况下添加到 FailedQueue
8. 从第 3 步开始循环

# 9. gevent: 协程
# 10. async: 协程
## 10.1 前置概念
1. async: async定义的函数会成为协程
2. await: async定义的函数中使用，通知loop此时可以调度出去了
    - 通常放一些io昂贵的操作
    - 协程(函数或对象) 、任务task、Future对象
3. yield:
    - 函数中使用，即将函数变成生成器
    - 函数的返回值变成迭代器
4. yield from: 两种用法
    - yield from 代替 await （为了兼容python老版本）
    - yield from 代替 for循环 + yield
5. 判断
    - asyncio.iscoroutine(): 不认yield from方法的协程
    - inspect.iscoroutine(): 认yield from方法的协程
    - asyncio.iscoroutinefunction(): 不认yield from方法的协程对象
    - inspect.iscoroutinefunction(): 认yield from方法的协程
6. 最佳实践
    - 自己用：async创建多个协程，main方法中通过task调度，最后asyncio.run(main())
    - 引用别人的: 先判断是否是协程对象，然后创建一个loop，调用loop.run_until_complete()
### 10.2 协程 Coroutines
1. 分为「协程函数」和「协程对象」，都叫协程
    - 协程函数: async定义的函数 或者 yield from+装饰器得到的函数
    - 协程对象: 协程函数的返回值（并不会调用协程）
2. 无论是协程函数还是协程对象都可以在await后面出现
    - 直接await一个协程，内部不会发生调度（需要await 一个task）
3. 通过asyncio.run(main())调用

**协程被运行的方法**

- asyncio.gather(协程1, 协程2)
- asyncio.wait_for(协程)
- asyncio.run(main())  # 只在最外层调用
- loop.run_until_complete(协程)
~~~python
# 两种定义协程的方法
# 通过async定义的协程
async def say_after(delay, what):
    await asyncio.sleep(delay)
    print(what)

# 通过yield from + 装饰器定义的协程
@asyncio.coroutine  # python3.4之前需要这么用，因为没有async关键字
def old_style_coroutine():
    yield from asyncio.sleep(1)
~~~
### 10.3 任务 task
1. 赋予协程被调度的能力
    - Task 对象被用来在事件循环中运行协程
    - 如果一个协程在等待一个 Future 对象，Task 对象会挂起该协程的执行并等待该 Future 对象完成
    - 当该 Future 对象 完成，被打包的协程将恢复执行
    - 创建后放到await后面，会自动放到loop（默认get_running_loop()）中被调用
2. 通过asyncio.create_task创建
    - loop.create_task()
    - ensure_future()
3. 是一个future对象的实用形式
    - Task 从 Future 继承了其除 set_result() 和 set_exception() 以外的所有 API
~~~python
import asyncio
import time

async def say_after(delay, what):
    await asyncio.sleep(delay)
    print(what)

# 这样执行无法并发执行，因为没有变成task，从而放到loop中
async def main():
    print(f"started at {time.strftime('%X')}")

    await say_after(1, 'hello')
    await say_after(2, 'world')

    print(f"finished at {time.strftime('%X')}")

# 这样可以并发执行，变成task之后可以放到loop中
async def main():
    # python3.7
    task1 = asyncio.create_task(say_after(1, 'hello'))
    task2 = asyncio.create_task(say_after(2, 'world'))
    print(f"started at {time.strftime('%X')}")
    await task1
    await task2
    print(f"finished at {time.strftime('%X')}")

asyncio.run(main())  # python3.7新功能，自动创建loop，并在结束时关闭
~~~
#### 10.3.1 cancel
> cancelled 方法进行判断
1. 这将安排在下一轮事件循环中抛出一个 CancelledError 异常给被封包的协程
2. 协程内部可以捕获这个错误，然后pass（不鼓励这样做）
~~~python
async def cancel_me():
    print('cancel_me(): before sleep')

    try:
        # Wait for 1 hour
        await asyncio.sleep(3600)
    except asyncio.CancelledError:
        print('cancel_me(): cancel sleep')
        raise
    finally:
        print('cancel_me(): after sleep')

async def main():
    # Create a "cancel_me" Task
    task = asyncio.create_task(cancel_me())

    # Wait for 1 second
    await asyncio.sleep(1)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("main(): cancel_me is cancelled now")

asyncio.run(main())

# Expected output:
#
#     cancel_me(): before sleep
#     cancel_me(): cancel sleep
#     cancel_me(): after sleep
#     main(): cancel_me is cancelled now
~~~
#### 10.3.2 done
#### 10.3.3 result
- 获取返回值或异常
    - 异常包括被取消的异常
- 如果 Task 对象的结果还不可用，此方法会引发一个 InvalidStateError 异常
#### 10.3.4 exception
- 被取消，引发 CancelledError 异常。
- 未完成，引发 InvalidStateError 异常。

### 10.4 Futures
1. 表示一种可等待的对象
2. 当一个 Future 对象 被等待，这意味着协程将保持等待直到该 Future 对象在其他地方操作完毕。
2. 使用时不建议自己创建futures对象，而是会由库和某些 asyncio API 暴露给用户，用作可等待对象
~~~python
async def main():
    # 使用方法1
    await function_that_returns_a_future_object()

    # 使用方法2
    await asyncio.gather(
        function_that_returns_a_future_object(),
        some_python_coroutine()
    )
~~~
### 10.5 loop
- 事件循环是每个 asyncio 应用的核心
- 事件循环会运行异步任务和回调，执行网络 IO 操作，以及运行子进程
- 设计理念是不把loop暴露出来，通过asyncio.run()通过最外层运行loop
- 库和框架的编写者需要更精细的控制loop行为时使用
#### 10.5.1 asyncio.get_running_loop
- 返回当前 OS 线程中正在运行的事件循环。
- 只能由协程调用

#### 10.5.2 asyncio.get_event_loop
1. 没有会创建并设置为当前时间循环
    - 该 OS 线程为主线程
    - asyncio.set_event_loop(loop) 还没有被调用
#### 10.5.3 asyncio.new_event_loop()
- 创建一个并设置为当前事件循环
~~~python
def _execute(self):
    result = self.func(*self.args, **self.kwargs)
    if asyncio.iscoroutine(result):
        loop = asyncio.new_event_loop()
        coro_result = loop.run_until_complete(result)
        return coro_result
    return result
~~~
#### 10.5.4 loop所属方法
- loop.run_until_complete(future)
    - 协程作为task运行(隐式转换)
- loop.run_forever()
    - 直到loop.stop()被调用
- loop.is_running()
- loop.is_closed()
- loop.close()
    - 非运行状态的loop调用
    - 立即关闭执行器，不会等待执行器完成
    - 幂等的和不可逆的。事件循环关闭后，不应调用其他方法
### 10.6 相关方法
#### 10.6.1 asyncio.run
> python 3.7 的功能
> python 3.9 更新为 loop.shutdown_default_executor()
- 此函数总是会创建一个新的事件循环并在结束时关闭之
- 它应当被用作 asyncio 程序的主入口点，理想情况下应当只被调用一次
~~~python
async def main():
    await asyncio.sleep(1)
    print('hello')

asyncio.run(main())
~~~
#### 10.6.2 asyncio.create_task
- 将 coro 协程 封装为一个 Task 并调度其执行
- 该任务会在 get_running_loop() 返回的循环中执行

#### 10.6.3 asyncio.sleep(delay)
- sleep() 总是会挂起当前任务，以允许其他任务运行
~~~python
# 以下协程示例运行 5 秒，每秒显示一次当前日期:
import asyncio
import datetime

async def display_date():
    loop = asyncio.get_running_loop()
    end_time = loop.time() + 5.0
    while True:
        print(datetime.datetime.now())
        if (loop.time() + 1.0) >= end_time:
            break
        await asyncio.sleep(1)  # 这里只有自己这个协程，所以只能等待

asyncio.run(display_date())
~~~
#### 10.6.4 asyncio.gather
- 一种不通过变成task，而调度协程的方法
- 接受多个协程对象，将返回值按顺序放到结果list中
- 还有一个 return_exceptions 参数
    - False 默认: 不影响其他协程
- gather 可以被取消，所有未完成的协程都会被取消
~~~python
import asyncio

async def factorial(name, number):
    f = 1
    for i in range(2, number + 1):
        print(f"Task {name}: Compute factorial({number}), currently i={i}...")
        await asyncio.sleep(1)
        f *= i
    print(f"Task {name}: factorial({number}) = {f}")
    return f

async def main():
    # Schedule three calls *concurrently*:
    L = await asyncio.gather(
        factorial("A", 2),
        factorial("B", 3),
        factorial("C", 4),
    )
    print(L)

asyncio.run(main())

# Expected output:
#
#     Task A: Compute factorial(2), currently i=2...
#     Task B: Compute factorial(3), currently i=2...
#     Task C: Compute factorial(4), currently i=2...
#     Task A: factorial(2) = 2
#     Task B: Compute factorial(3), currently i=3...
#     Task C: Compute factorial(4), currently i=3...
#     Task B: factorial(3) = 6
#     Task C: Compute factorial(4), currently i=4...
#     Task C: factorial(4) = 24
#     [2, 6, 24]
~~~
#### 10.6.5 asyncio.shield
- 屏蔽取消
    - res = await shield(something())
    - something内部不会被取消
- something内部依然可以取消
#### 10.6.6 asyncio.wait_for & wait
> asyncio.wait python3.8 被移除
- timeout=None
    - 此函数不会引发 asyncio.TimeoutError
- return_when=ALL_COMPLETED
    FIRST_COMPLETED
    FIRST_EXCEPTION
    ALL_COMPLETED
- wait 在超时发生时不会取消可等待对象
~~~python
async def foo():
    return 42

task = asyncio.create_task(foo())
done, pending = await asyncio.wait({task})

if task in done:
    # Everything will work as expected now.
~~~
#### 10.6.7 asyncio.as_completed(aws, *, timeout=None)
1. 返回一个协程的迭代器
2. 所返回的每个协程可被等待以从剩余的可等待对象的可迭代对象中获得最早的下一个结果
3. 如果在所有 Future 对象完成前发生超时则将引发 asyncio.TimeoutError
~~~python
for coro in as_completed(aws):
    earliest_result = await coro
    # ...
~~~
#### 10.6.8 asyncio.current_task()
- 获取当前loop的正在运行的task
- 传入loop，或者自动获取当前loop
#### 10.6.8 asyncio.all_tasks()
- 获取当前loop中的所有task
- 传入loop，或者自动获取当前loop

### 10.7 请求中的异步
#### 10.7.1 aiohttp
~~~python
# 可以做客户端去请求，也可以启动服务端
# 以下是客户端的例子
import aiohttp
import asyncio

async def main():

    async with aiohttp.ClientSession() as session:
        async with session.get('http://python.org') as response:

            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.text()
            print("Body:", html[:15], "...")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
~~~
#### 10.7.2 httpx
~~~python
# python3.6开始的
async def main():
    async with httpx.AsyncClient() as client:
        tasks = (client.get(url) for url in urls)
        regs = await asyncio.gather(*tasks)
    htmls = [req.text for req in reqs]

asyncio.run(main())
~~~

# 11. Threading: 线程
## 11. 线程内while True实现异步非阻塞效果
~~~python
class PubSubWorkerThread(threading.Thread):
    def __init__(self, pubsub, sleep_time, daemon=False):
        super(PubSubWorkerThread, self).__init__()
        self.daemon = daemon
        self.pubsub = pubsub
        self.sleep_time = sleep_time
        self._running = threading.Event()

    def run(self):
        if self._running.is_set():
            return
        self._running.set()
        pubsub = self.pubsub
        sleep_time = self.sleep_time
        while self._running.is_set():  # 线程内whlie True
            # get_message 会用回调函数处理请求
            pubsub.get_message(ignore_subscribe_messages=True,
                               timeout=sleep_time)
        pubsub.close()

    def stop(self):
        # trip the flag so the run loop exits. the run loop will
        # close the pubsub connection, which disconnects the socket
        # and returns the connection to the pool.
        self._running.clear()
# 使用
thread = PubSubWorkerThread(self, sleep_time, daemon=daemon)
thread.start()
return thread
~~~

