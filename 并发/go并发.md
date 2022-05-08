# 1. 信号与唤醒: 管道
**讨论**
1. 接收者阻塞在「接收channel」的位置
2. 发送者向该channel发送消息后会唤起接收协程

**深入讨论**
- 等待从通道中接收值会让协程进入 Gwaiting 状态
- 被唤醒后进入 Grunnable 状态等待调度器调度
- 一般使用 chan struct{}类型，不占内存
- close(ch)被生产者调用，<-会立即返回
	- 关闭后再发数据会panic

**代码**
~~~go
symbolChan := make(chan struct{})
// 1. 简单使用
// 阻塞等待信号
go func waitForSymbol() {
    <- symbolChan
    ...
}()

// 发送信号
func sendSymbol() {
    symbolChan <- struct{}{}
    ...
}

// 2. 复杂应用：遍历chan
func main() {
  num := 4
  var chs []chan struct{}
  // 4 个work
  for i := 0; i < num; i++ {
    chs = append(chs, make(chan struct{}))
  }
  
  for i := 0; i < num; i++ {
    go func(label int, cur, next chan struct{}) {
      for {
        <-cur
        fmt.Println(label)
        time.Sleep(time.Second)
        next <- struct{}{}
      }
    }(i, chs[i], chs[(i+1)%num])
  }

  chs[0] <- struct{}{}
  select {}  // 做个阻塞
}
~~~

# 2. 信号与唤醒: 条件变量
**讨论**
1. 绑定一个锁（读写锁或者普通mutex)
2. cond.Wait() 挂起  cond.Signal()通知

**深入讨论**
- cond.Wait() 之前需要锁定关联的锁
- cond.Wait() 执行完之后需要解锁

**代码**
~~~go
var mutex sync.Mutex
var cond = sync.NewCond(mutex)

go func() {
    mutex.Lock()  // wait之前必须锁定与之关联的锁，否则panic
    defer mutex.Unlock()  // wait之后必须释放与之关联的锁
    cond.Wait()
    fmt.Println("收到")
}()

cond.Signal()
~~~

# 3. 信号与唤醒：信号
~~~go
func main() {
    var closing = make(chan struct{})
    var closed = make(chan struct{})

    go func() {
        // ... 执行业务逻辑
    }()
    
    // 处理 CTRL+C 等中断信号
    termChan := make(chan os.Signal)
    signal.Notify(termChan, syscall.SIGINT, syscall.SIGTERM) // 
    <- termChan
    
    close(closing)
    go func(closed chan struct{}) {
        // 优雅退出
    }(closed)
    
    select {
        case <-closed:
        case <-time.After(time.Second):
            fmt.Println("timeout")
    }
}
~~~
# 4. 并发与同步：waitGroup
**讨论**
1. wg.Add(1) 与 wg.Done() 成对出现
2. wg.Wait() 会阻塞直到wg.Add()的内容都被Done了

**深入讨论**
- wg对象不应该被复制
- cond.Wait() 执行完之后需要解锁

**代码**
~~~go
var wg sync.WaitGroup

for _, handler := range handlers {
    wg.Add(1)
    handler_ := handler
    go func() {
        defer wg.Done()
        if err := handler_.Handle(msg); err != nil {
            log.V2.Error().With(context.Background()).Str("Process kafka consumer message failed, error:").Error(err).Emit()
        }
    }()
}

wg.Wait()
~~~

# 5. 锁mutex: 悲观锁
**讨论**
1. 通过mutex锁保护一个共享变量，比如同时增加
2. 升级为读写锁（场景很少）：
    - var rwm sync.RWMutex
    - rwm.RLock()
    - rwm.RUnlock()
    * 读写锁的读锁，可以进一步升级成 atomic.LoadInt64(&value)
3. 分布式锁（通过redis、或其他数据中间件）讨论
    - 解了不是自己的锁
    - 协程挂掉了没有解锁

**深入讨论**
- 锁的零值就是一个可用的锁了
- 尝试锁一个未解锁的锁，会阻塞到释放
- 尝试解锁一个未上锁的锁，会panic 且无法被recover
- 读写锁内部也是一种mutex，都是基于信号量实现

**代码**
~~~go
var mutex sync.Mutex
func write() {
    mutex.Lock()
    defer mutex.Unlock()
    ...
}
~~~

# 6. 锁CAS: 乐观锁
**讨论**
1. 相比mutex系列，CAS是一种乐观锁，没有加解锁的性能消耗，但可能不容易成功
2. 乐观锁能做的比较有限

**代码**
~~~go
var value int32 = 10
func addValue(delta int32) {
    var v int32
    for {
        if atomic.CompareAndSwapIntew(&value, v, (v+delta)) {
            break
        }
    }
}
~~~

# 7. 原子操作
**讨论**
1. 简单操作，如数字加减一个常数可以不通过加锁来实现

**深入讨论**
- AddUint32 和 AddUint64 不支持负数
    - atomic.AddUint32(&ui32, ^uint32(-NN-1))
    - atomic.AddUint64(&ui64, ^uint64(-NN-1))

**代码**
~~~go
var oldi32 int32 = 0
newi32 := atomic.AddInt32(&oldi32, 3)  
newi32 := atomic.AddInt32(&oldi32, -3)
~~~

# 8. 原子值
**讨论**
1. go提供的类似语法糖的操作，允许任意类型作为原子值
2. Load和Set操作需要使用原子操作

**深入讨论**
- 不要复制原子值（不会报错，但是go vet会检测出），要传递指针
- Set操作用到了写时复制的技巧，即 Load -> set -> Store
    - 读写分离的无锁化方案
    - 被修改的内容很大会造成很大的性能损耗

**代码**
~~~go
// 初始化
var val atomic.Value
val.Store(make([]int, 10))

// 设置值  val[index] = elem
newArray := make([]int, len(val))
copy(newArray, val.Load().([]int))
newArray[index] = elem
val.Store(newArray)

// 读取值: val[index]
val.Load().([]int)[index]
~~~

# 9. 单例
**讨论**
1. Once.Do()可以做到并发时也只执行一次
2. 实现方式是：卫述语句、双重检查锁定、共享标记的原子读写
3. 常用与对象的全局单例实例化

**代码**
~~~go
var (
	stateMachineDal     *StateMachineDal
	stateMachineDalOnce sync.Once
)

func GetStateMachineDal() *StateMachineDal {
	stateMachineDalOnce.Do(func() {
		stateMachineDal = &StateMachineDal{
			Db: model.GetMysqlDb(),
		}
	})
	return stateMachineDal
}
~~~

# 10. 临时对象池
**讨论**
1. 当做简单的缓存来用
2. 随着下次GC消失
3. 比较鸡肋，使用参考bigcache

**代码**
~~~go
defer debug.SetGCPercent(debug.SetGCPercent(-1))  // 禁用GC
var count int32
newFunc := func() interface{} {
    return atomic.AddInt32(&count, 1) 
}
pool := sync.Pool{New: newFunc} // New字段初始化的时候，放了一个值
v1 := pool.Get()  // 此时就是1
runtime.GC()  // 此时之前的值就都没了
~~~

# 11. 超时控制
**讨论**
1. select在timeout和result  chan中做选择
	- 可以不给default，阻塞在这里
2. time.After(80 * time.Millisecond) 得到一个chan
**代码**
~~~go
// 工厂模式
var (
        Web = fakeSearch("web")
        Image = fakeSearch("image")
        Video = fakeSearch("video")
)

type Search func(query string) Result

func fakeSearch(kind string) Search {
	return func(query string) Result {
				time.Sleep(time.Duration(rand.Intn(100)) * time.Millisecond)
				return Result(fmt.Sprintf("%s result for %q\n", kind, query))
	}
}

// 核心代码
func Google(query string) (results []Result) {
	c := make(chan Result)
	go func() { c <- Web(query) } ()
	go func() { c <- Image(query) } ()
	go func() { c <- Video(query) } ()

	timeout := time.After(80 * time.Millisecond)
	for i := 0; i < 3; i++ {
		select {
		case result := <-c:
			results = append(results, result)
		case <-timeout:
			fmt.Println("timed out")
			return
		}
	}
	return
}
~~~

# 12. context
## 12.1 cancel
**讨论**
0. 在1.7版本引入。用来简化在多个go routine传递上下文数据、(手动/超时)中止routine树等操作
	- 比如，官方http包使用context传递请求的上下文数据
	- gRpc使用context来终止某个请求产生的routine树
1. context.WithCancel(ctx) 返回一个可以取消的子ctx和取消的方法
2. 调用cancel()后，ctx.Done()管道就会有内容（可以取消子context）
3. 其本质是通过 for select 对ctx.Done()监听，提前返回
	- 并不能kill掉正在运行的goroutine，只是可以提前返回不让调用方阻塞住

**深入讨论**
1. Context 通过关闭通道的方式，将取消任务的信息告诉了子协程
2. 上层 Context 被取消后会沿着树向下递归（深度优先）的告知所衍生的所有 Context 该任务被取消
3. Context 还可以携带 kv 在任务中传递
4. 取消操作应该是建议性质的
	- 调用者并不知道被调用者内部实现，调用者不应该 interrupt/panic 被调用者
	- 调用者应该通知被调用者处理不再必要，被调用者来决定如何处理后续操作
4. 使用方法
	- Done会返回一个channel，当该context被取消的时候，该channel会被关闭，同时对应的使用该context的routine也应该结束并返回。
	- Context中的方法是协程安全的，这也就代表了在父routine中创建的context，可以传递给任意数量的routine并让他们同时访问。
	- Deadline会返回一个超时时间，routine获得了超时时间后，可以对某些io操作设定超时时间。
	- Value可以让routine共享一些数据，当然获得数据是协程安全的。

**使用方式**
1. 通过context.Background() / context.TODO() 创建根ctx
	- 都是emptyCtx 类型的值
	- emptyCtx是 int的别名，实现了ctx的接口：Deadline() / Done() / Err() / Value(key)
2. 通过WithCancel / WithDeadline / WithTimeout / WithValue 创建子context
	- context.WithCancel(context.Background())
	- context.WithTimeout(parent Context, timeout time.Duration)
	- context.WithValue(parent Context, key, val interface{})
**代码**
~~~go
// 外界取消
func TestWithCancel(t *testing.T) {
   ctx, cancel := context.WithCancel(context.Background())
   go func(ctx context.Context) {
      for {
         select {
         case <-ctx.Done():
            fmt.Println("监控退出，停止了...")
            return
         default:
            fmt.Println("goroutine监控中...")
            time.Sleep(2 * time.Second)
         }
      }
   }(ctx)
   time.Sleep(5 * time.Second)
   fmt.Println("可以了，通知监控停止")
   cancel()
   time.Sleep(5 * time.Second)
}

// ms平台的基础实现
func RPCTimeoutMW(next endpoint.EndPoint) endpoint.EndPoint {
   return func(ctx context.Context, request interface{}) (interface{}, error) {
      rpcInfo := GetRPCInfo(ctx)
      ctx, cancel := context.WithTimeout(ctx, time.Duration(rpcInfo.RPCTimeout)*time.Millisecond)
      defer cancel()

      var resp interface{}
      var err error
      done := make(chan error, 1)
      go func() {
         defer func() {
            if err := recover(); err != nil {
               const size = 64 << 10
               buf := make([]byte, size)
               buf = buf[:runtime.Stack(buf, false)]

               logs.CtxError(ctx, "KITC: panic: to=%s, toCluster=%s, method=%s, Request: %v, err: %v\n%s",
                  rpcInfo.To, rpcInfo.ToCluster, rpcInfo.Method, request, err, buf)

               done <- fmt.Errorf("KITC: panic, %v\n%s", err, buf)
            }
            close(done)
         }()

         resp, err = next(ctx, request)
      }()

      select {
      case panicErr := <-done:
         if panicErr != nil {
            panic(panicErr.Error()) // throws panic error
         }
         return resp, err
      case <-ctx.Done():
         return nil, makeTimeoutErr(rpcInfo)
      }
   }
}
~~~

# 最佳实践：mutex和channel
1. 简单的数据保护使用mutex
	- mutex的效率比channel高
	- 因为通道是使用内存访问同步来操作，所以它必然只会更慢
2. 复杂功能使用channel
	- 消息传递
	- 生产者消费者模型
	- select功能、超时功能

# 最佳实践：waitGroup+err处理的封装
~~~go
// 定义
type WaitGroupWrapper struct {
	sync.WaitGroup
	ctx context.Context
}

func GetWaitGroupWrapper(ctx context.Context) *WaitGroupWrapper {
	return &WaitGroupWrapper{ctx: ctx}
}

func (wg *WaitGroupWrapper) Wrap(f func()) {
	wg.Add(1)
	go func() {
		defer wg.Done()
		safeRun(f, wg.ctx)
	}()
}

// Avoid panic.
func safeRun(fun func(), ctx context.Context) {
	defer func() {
		if err := recover(); err != nil {
			stack := string(debug.Stack())
			GetLogger(ctx).Errorf("[safeRun] Goroutine Recover: %+v, stack is %v", err, stack)
		}
	}()
	fun()
}

// 使用
wg := tools.GetWaitGroupWrapper(ctx)
wg.Wrap(func() {

})
wg.Wait()
~~~

# 最佳实践：bigcache的封装
~~~go
package cache

import (
	"sync"
	"time"

	"github.com/allegro/bigcache/v2"
)

const expireTimeKey = "cache_expire_time"

var (
	cache      *Cache
	cacheOnce  sync.Once
	expireTime *time.Duration
)

type Cache struct {
	bigCache *bigcache.BigCache
}

func GetCache(ctx context.Context) (*Cache, error) {
	if expireTime == nil {
		tmp := time.Duration(10000) * time.Minute
		expireTime = &tmp
	}

	return mustNewCache(*expireTime), nil

}

func (c *Cache) GetFromCacheCouldBeNil(key string) ([]byte, error) {
	val, err := c.bigCache.Get(key)
	if err == nil {
		return val, nil
	}

	if err == bigcache.ErrEntryNotFound {
		return nil, nil
	}

	return nil, err
}

func (c *Cache) SetToCache(key string, val []byte) error {
	return c.bigCache.Set(key, val)
}

func (c *Cache) Delete(key string) error {
	return c.bigCache.Delete(key)
}

func mustNewCache(eviction time.Duration) *Cache {
	cacheOnce.Do(func() {
		cache = newBigCache(eviction)
	})

	return cache
}

func newBigCache(eviction time.Duration) *Cache {
	cacheConfig := bigcache.DefaultConfig(eviction)

	bigCache, err := bigcache.NewBigCache(cacheConfig)
	if err != nil {
		panic(err)
	}

	return &Cache{bigCache: bigCache}
}
~~~

# 最佳实践 channel作为主loop
~~~go
func ConsumerLoop() {
	for {
		select {
		case msg, more := <-consumer.Messages():
			if more {
				log.V2.Info().With(context.Background()).Str("Consumed message:").Str(string(msg.Value)).Emit()
				consumer.MarkOffset(msg, "")
				handleConsumeMessage(msg)
			}
		case err, more := <-consumer.Errors():
			if more {
				log.V2.Error().With(context.Background()).Str("Received kafka message failed, error:").Error(err).Emit()
			}
		case notify, more := <-consumer.Notifications():
			if more {
				if len(notify.Claimed) > 0 || len(notify.Released) > 0 || len(notify.Current) > 0 {
					log.V2.Info().
						With(context.Background()).
						Str("Received kafka consumer notification.").
						Str("Claimed:").
						Obj(notify.Claimed).
						Str("Released:").
						Obj(notify.Released).
						Str("Current:").
						Obj(notify.Current).
						Emit()
				}
			}
		case <-consumerClose:
			log.V2.Info().With(context.Background()).Str("Consumer will close").Emit()
			return
		}
	}
}
~~~

# 附录1：利用chan实现锁
1. 一个缓冲区的 struct{}的chan
2. 满了放内容和空了去内容都会阻塞
	- 取不出来就拉倒：配一个空的default
	- 取不出来就报错：配一个panic的default
	- 超时管理：配一个
~~~go
type Mutex struct {
    ch chan struct{}
}

// 使用锁需要初始化
func NewMutex() *Mutex {
    mu := &Mutex{make(chan struct{}, 1)}
    mu.ch <- struct{}
    return mu
}

// 请求锁，直到获取到锁
func(m *Mutex) Lock() {
    <-mu.ch
}

// 释放锁
func(m *Mutex) Unlock() {
    select {
    case m.ch <- struct{}{}:
    default:
        // 当 case 阻塞时，意味着锁本身并没有被取走
        panic("unlock of unlocked mutex")
    }
}

// 尝试获取锁
func (m *Mutex) TryLock() bool {
    select {
    case <- m.ch:
        return true
    default:
        // 取锁失败不至于被阻塞
    }
    return false
}

// 取锁加入超时控制
func (m *Mutex) LockTimeout(timeout time.Duration) bool {
	// time.After()返回的就是time.NewTimer().C
	// timer 支持 timer.reset(3*time.Second)
    timer := time.NewTimer(timeout)
    select {
    case <-m.ch:
        timer.Stop()
        return true
    case <-time.C:
    }
    return false
}

func (m *Mutex) IsLocked() bool {
    return len(m.ch) == 0
}
~~~
# 附录2：利用chan实现生成器
1. 通过一个缓冲区为0的通道
	- 如果没有获取的方法，c <- *v会一直阻塞
2. 最后要close()，否则取不出来就会死锁(一直显式等待)
3. 是否要把chan传到go func里面都行
	- 虽然make 返回的是map、slice、chan本身，但其本身就是指针类型
	- 最后返回的是chan，但是chan是指针类型
4. 使用时直接用 for item := range Iterator(list) 即可
	- 不用for _, item := 
~~~go
func (bc *BlockChain) Iterator() <-chan Block {
	c := make(chan Block)
	go func() {
		currentHash := bc.TailHash
		for {
			if len(currentHash) == 0 {
				break
			}
			for _, v := range bc.Blocks {
				if bytes.Equal(v.Hash, currentHash) {
					c <- *v
					currentHash = v.PrevHash
				}
			}
		}
		close(c)
	}()
	return c
}
~~~