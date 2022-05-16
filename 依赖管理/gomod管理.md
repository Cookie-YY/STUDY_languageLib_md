# 背景信息
1. 1.11的特性，支持任意位置建立源码
    - $GOPATH的子目录下的项目：go mod init 名称是src路径下的相对路径
    - 非$GOPATH的子目录，go mod init 的内容和路径无关
2. go env -w GO111MODULE=on  # 修改go相关的环境变量
3. 依赖包位置：$GOPATH/pkg
4. go.sum文件记录依赖树

# 1. 启动一个项目
~~~bash
go mod download  # 下载所有依赖
~~~

# 2. 开发一个项目
1. 支持 go run 自动下载依赖
    - 拉取最新的tag
    - 没有tag，拉取最新commit
~~~bash
# 初始化项目
go mod init project  # go.mod文件中标识 module project

# 安装依赖
go get xx/xx  # 下载模块
go mod tidy   # 拉取缺少的模块，移除不用的模块
go get -u     # 升级所有依赖
go get package@version  # 升级指定版本
~~~

# 其他
## vendor
~~~bash
go vendor  # 将依赖放到当前目录
go build -mod vendor  # 以当前目录下的依赖进行打包
~~~

## 发布
~~~bash
# 1. 初始化
go mod init github.com/xx/xx  # 跟github上创建的项目路径一致

# 2. git 推送
git tag v1.0.0
git push --tags

# 3. 使用
# 3.1 go中引入
import (
    "github.com/xx/xx"
)
# 3.2 下载
go mod init importtest  # 会自动下载1.0.0的版本
go run

# 4. 升级
go get -u  # 更新到最新的版本
go get -u=patch  # 更新到 1.0.1 不会更新到1.1,0
go get package@v1.1.0  # 指定版本

# 大版本的升级不会被更新，需要手动指定
import (
    "github.com/xx/xx/v2"
)
~~~
g