# 1. 交叉编译
1. GOOS：目标平台的操作系统（darwin、freebsd、linux、windows）
2. GOARCH：目标平台的体系架构（386、amd64、arm）
## 1.1 mac下编译
~~~bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build main.go
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build main.go
~~~
## 1.2 win下编译
~~~bash
SET CGO_ENABLED=0
SET GOOS=darwin
SET GOARCH=amd64
go build main.go

SET CGO_ENABLED=0
SET GOOS=linux
SET GOARCH=amd64
go build main.go
~~~
## 1.3 linux下编译
~~~bash
CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build main.go
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build main.go
~~~

# client单例初始化
1. 定义全局变量
    - Client 客户端变量
    - sync.Once 变量
2. 定义newClient方法，改变全局的Client变量
3. getClient方法中，once调用newClient方法，并返回全局变量Client
~~~go
type TCCClient struct {
	tccClient *tccclient.ClientV2
}

var (
	tccClient *TCCClient
	tccOnce   sync.Once
)

func GetTccClient() *TCCClient {
	tccOnce.Do(func() {
		tccClient = newTCCClient(GetConfig().TCC.ConfigName, GetConfig().TCC.ConfigSpace)
	})
	return tccClient
}

func (t *TCCClient) TCCGetValue(ctx context.Context, key string) (string, error) {
	return t.tccClient.Get(ctx, key)
}

func (t *TCCClient) TCCGetMapValue(ctx context.Context, key string, mapPtr interface{}) error {
	mapStr, err := t.TCCGetValue(ctx, key)
	if err != nil {
		return err
	}
	err = json.Unmarshal([]byte(mapStr), mapPtr)
	if err != nil {
		return err
	}
	return nil
}

func newTCCClient(configName string, configSpace string) *TCCClient {
	config := tccclient.NewConfigV2()
	config.Confspace = configSpace
	client, err := tccclient.NewClientV2(configName, config)
	if err != nil {
		panic(err)
	}
	return &TCCClient{tccClient: client}
}

~~~