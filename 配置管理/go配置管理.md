# 1. viper
## 1.1 配置文件
1. yaml中不区分整数还是字符串，都没有引号，由GetString或GetInt区分
2. 读不进来不会报错，返回零值
    - viper.IsSet() 进行检查
3. bool值小写（true）用GetBool方法
4. 最佳实践
    1. 写一个结构体
    2. 监听改变写到结构体
~~~go
// 1. 加载
import (
    "github.com/spf13/viper"
    "path/filepath"
)
env := strings.ToLower(os.Getenv("SMART_INSIGHT_ENV"))
confPath := fmt.Sprintf("config.%s.yaml", env)
viper.SetConfigFile(filepath.Join("conf", confPath))
err := viper.ReadInConfig()

// 2. 使用
viper.GetString("Message.LogDir")
viper.GetInt("MYSQL.port")
~~~

## 1.2 环境变量
~~~go
// 1. 设置前缀：自动转为大写
viper.SetEnvPrefix("spf") // 将自动转为大写
// 2. 方法1：绑定变量
viper.BindEnv("id")  // viper.BindEnv("id", "spf")  第二个参数是前缀，制定了就不用再写
// 2. 方法2：自动检查所有前缀
viper.AutomaticEnv() 
// 3. 设置环境变量
os.Setenv("SPF_ID", "13") // 通常是在应用程序之外完成的
id := viper.Get("id") // 13
~~~
## 1.3 高级
### 1.3.1 监听配置
~~~go
viper.WatchConfig()
viper.OnConfigChange(func(e fsnotify.Event) {
  // 配置文件发生变更之后会调用的回调函数
	fmt.Println("Config file changed:", e.Name)
})
~~~
### 1.3.2 子配置
~~~go
func NewCache(cfg *Viper) *Cache
cfg1 := viper.Sub("app.cache1")
cache1 := NewCache(cfg1)

cfg2 := viper.Sub("app.cache2")
cache2 := NewCache(cfg2)
~~~

### 1.3.3 反序列化到结构体
~~~go
type config struct {
	Port int
	Name string
	PathMap string `mapstructure:"path_map"`
}

var C config

err := viper.Unmarshal(&C)
if err != nil {
	t.Fatalf("unable to decode into struct, %v", err)
}
~~~
### 1.3.4 最佳实践
~~~go
package main

import (
	"fmt"
	"net/http"

	"github.com/fsnotify/fsnotify"

	"github.com/gin-gonic/gin"
	"github.com/spf13/viper"
)

type Config struct {
	Port    int    `mapstructure:"port"`
	Version string `mapstructure:"version"`
}

var Conf = new(Config)

func main() {
	viper.SetConfigFile("./conf/config.yaml") // 指定配置文件路径
	err := viper.ReadInConfig()               // 读取配置信息
	if err != nil {                           // 读取配置信息失败
		panic(fmt.Errorf("Fatal error config file: %s \n", err))
	}
	// 将读取的配置信息保存至全局变量Conf
	if err := viper.Unmarshal(Conf); err != nil {
		panic(fmt.Errorf("unmarshal conf failed, err:%s \n", err))
	}
	// 监控配置文件变化
	viper.WatchConfig()
	// 注意！！！配置文件发生变化后要同步到全局变量Conf
	viper.OnConfigChange(func(in fsnotify.Event) {
		fmt.Println("夭寿啦~配置文件被人修改啦...")
		if err := viper.Unmarshal(Conf); err != nil {
			panic(fmt.Errorf("unmarshal conf failed, err:%s \n", err))
		}
	})

	r := gin.Default()
	// 访问/version的返回值会随配置文件的变化而变化
	r.GET("/version", func(c *gin.Context) {
		c.String(http.StatusOK, Conf.Version)
	})

	if err := r.Run(fmt.Sprintf(":%d", Conf.Port)); err != nil {
		panic(err)
	}
}
~~~
# 2. configor
## 2.1 定义
~~~go
package config

import (
	"os"
	"sync"

	"github.com/jinzhu/configor"
)

type MQConfig struct {
	Group   string `yaml:"group"`
	Topic   string `yaml:"topic"`
	Cluster string `yaml:"cluster"`
}

type Config struct {
	Mysql struct {
		PSM    string `yaml:"psm"`
		DBName string `yaml:"db_name"`
		URL    string `yaml:"url"`
		Table  string `yaml:"table"`
	} `yaml:"mysql"`
	ByteFlowMq struct {
		PSM          string   `yaml:"psm"`
		ForecastMQ   MQConfig `yaml:"forecast"`
		TaskMQ       MQConfig `yaml:"task"`
		AutoAcceptMQ MQConfig `yaml:"auto_accept"`
		StartFlowMQ  MQConfig `yaml:"start_flow"`
		Subscriber   string   `yaml:"subscriber"`
	} `yaml:"byte_flow_mq"`
}

var (
	config      *Config
	ServiceName = os.Getenv("TCE_SERVICE_NAME")
)

func initConfig() {
	env := GetEnv()

	conf := &Config{}
	err := configor.New(&configor.Config{Environment: env}).Load(conf, "./conf/config.yaml")
	if err != nil {
		panic(err)
	}
	config = conf
}

var once sync.Once

func GetConfig() *Config {
	once.Do(initConfig)
	return config
}
~~~
## 2.2 使用
具体使用时通过 sync.Once 或 init方法内进行单例实例化
~~~go
config.GetConfig().Mysql
~~~

# yaml

~~~go
var Config Conf  // Conf是一个结构体，标好了yaml信息

env := strings.ToLower(os.Getenv("SMART_INSIGHT_ENV"))
configPath := fmt.Sprintf("conf/config.%s.yaml", env)
configFile, err := ioutil.ReadFile(configPath)
if err != nil {
	return err
}
err = yaml.Unmarshal(configFile, &Config)
if err != nil {
	return err
}
return err
~~~
