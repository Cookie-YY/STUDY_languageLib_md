# 1. 缓存
# 2. redis与pickle
~~~python
class DefaultSerializer:
    dumps = partial(pickle.dumps, protocol=pickle.HIGHEST_PROTOCOL)
    loads = pickle.loads
# 存
res = DefaultSerializer.dumps(some_object)
redis_client.set("key", res)
# 取
res = redis_client.get("key")
some_object = DefaultSerializer.loads(res)
~~~
# 3. 基于subscribe的异步IO
1. 同步阻塞: redis.Redis().blpop(key_list)
    - 一个可以导致hang住的操作
2. 同步非阻塞: while True + redis.Redis(key).lpop
    - 不停轮询问数据
    - 可以使用多线程/协程 的方式实现类似异步非阻塞的效果
3. 异步阻塞IO: redis.Redis(key_list).subscribe
    - 订阅的模式，使用listen进行阻塞
4. 异步非阻塞IO: redis.Redis(key_list).subscribe
    - 订阅的模式，有数据通知，而不是轮询
## 3.1 blpop的阻塞【同步阻塞】
- 通过blpop的方式
~~~python
"""
rq中封装的lpop方法
1. 如果worker没有开启burst（干完了等着），就用blpop阻塞在哪趴活
2. 如果worker开启burst了（干完了自杀），就用lpop一次性拿一个任务
"""
def lpop(cls, queue_keys, timeout, connection=None):
    # connection不为None就返回 connection，否则返回local栈顶的元素
    connection = resolve_connection(connection)
    if timeout is not None:  # blocking variant   没有burst时
        if timeout == 0:
            raise ValueError('RQ does not support indefinite timeouts. Please pick a timeout value > 0')
        result = connection.blpop(queue_keys, timeout)
        if result is None:
            raise DequeueTimeout(timeout, queue_keys)
        queue_key, job_id = result
        return queue_key, job_id
    
    else:  # non-blocking variant   设置了burst
        for queue_key in queue_keys:
            blob = connection.lpop(queue_key)
            if blob is not None:
                return queue_key, blob
        return None
~~~
## 3.2 轮询的阻塞【同步非阻塞】
- 方法1: 通过轮询 + lpop的方式
- 方法2: 通过订阅 + 轮询 + get_message的方式
~~~python

~~~
## 3.3 轮询+多线程的非阻塞【同步非阻塞】
- 将3.2中轮询的过程通过多线程的方式放到后台
## 3.4 订阅模式的阻塞【异步阻塞】
- 基于subscribe + listen的方式
~~~python
import time
import redis

rc = redis.StrictRedis(host='****', port='6379', db=3,     password='******')
ps = rc.pubsub()
ps.subscribe('liao')  #从liao订阅消息
for item in ps.listen():        #监听状态：有消息发布了就拿过来
    if item['type'] == 'message':
        print(item['channel'])
        print(item['data'])
~~~
## 3.5 订阅的非阻塞【异步非阻塞】
- 基于subscribe + 注册回调的方式
1. 订阅一堆keys，绑定一个函数
2. 函数中是在新的线程的处理函数

**核心**
1. 发送信息
    - connection.publish(key, data)
    - data就是字符串
2. 绑定回调并异步执行
    - pubsub = connection.pubsub()
    - pubsub.subscribe(key=func)
    - pubsub.run_in_thread(sleep_time=0.2, daemon=True)
3. 解析信息
    - json.loads(payload.get('data').decode())
~~~python
def subscribe(self):
    """Subscribe to this worker's channel"""
    self.log.info('Subscribing to channel %s', self.pubsub_channel_name)
    # 1. 获取pubsub
    self.pubsub = self.connection.pubsub()
    # 2. 订阅keys并绑定处理函数
    self.pubsub.subscribe(**{self.pubsub_channel_name: self.handle_payload})
    # 3. 异步执行
    self.pubsub_thread = self.pubsub.run_in_thread(sleep_time=0.2, daemon=True)

def handle_payload(self, message):
    """Handle external commands"""
    self.log.debug('Received message: %s', message)
    payload = parse_payload(message)
    handle_command(self, payload)

def parse_payload(payload):
    """Returns a dict of command data"""
    return json.loads(payload.get('data').decode())

def handle_command(worker, payload):
    """Parses payload and routes commands"""
    if payload['command'] == 'stop-job':
        handle_stop_job_command(worker, payload)
    elif payload['command'] == 'shutdown':
        handle_shutdown_command(worker)
    elif payload['command'] == 'kill-horse':
        handle_kill_worker_command(worker, payload)

def send_command(connection, worker_name, command, **kwargs):
    payload = {'command': command}
    if kwargs:
        payload.update(kwargs)
    connection.publish(PUBSUB_CHANNEL_TEMPLATE % worker_name, json.dumps(payload))
~~~