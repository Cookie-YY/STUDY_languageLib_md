# cProfile
- 生成prof文件，分析调用耗时，[参考链接](https://zhuanlan.zhihu.com/p/24495603)
## 快速使用
~~~python
def do_cprofile(filename):
    """
    Decorator for function profiling.
    """
    def wrapper(func):
        def profiled_func(*args, **kwargs):
            # Flag for do profiling or not.
            DO_PROF = ENV == "dev"
            if DO_PROF:
                profile = cProfile.Profile()
                profile.enable()
                result = func(*args, **kwargs)
                profile.disable()
                # Sort stat by internal time.
                sortby = "tottime"
                ps = pstats.Stats(profile).sort_stats(sortby)
                ps.dump_stats(filename)
            else:
                result = func(*args, **kwargs)
            return result
        return profiled_func
    return wrapper

@do_cprofile("./test.prof")
def run():
    pass
~~~
## api使用
- strip_dirs(): 删除报告中所有函数文件名的路径信息
- dump_stats(filename): 把stats中的分析数据写入文件（效果同cProfile.Profile.dump_stats())
- sort_stats(*keys): 对报告列表进行排序，函数会依次按照传入的参数排序，关键词包括calls, cumtime等，具体参数参见https://docs.python.org/2/library/profile.html#pstats.Stats.sort_stats
- reverse_order(): 逆反当前的排序
- print_stats(*restrictions): 把信息打印到标准输出。*restrictions用于控制打印结果的形式, 例如(10, 1.0, ".*.py.*")表示打印所有py文件的信息的前10行结果。
~~~python
import pstats
p = pstats.Stats("test.prof")
p.strip_dirs().sort_stats("cumtime").print_stats(10, 1, ".*")  # 按照累积时间进行降序排序并输出了前十行
p.strip_dirs().sort_stats("time").print_stats(10, 1, ".*")  # 打印内部耗时最多的10个函数（不包含子函数）
~~~
![](https://pic1.zhimg.com/v2-611bc1e629ccb3be52e2fffc7566ef20_r.jpg)
## 解释
- ncalls表示函数调用的次数（有两个数值表示有递归调用，总调用次数/原生调用次数）
- tottime是函数内部调用时间（不包括他自己调用的其他函数的时间）
- percall等于 tottime/ncalls
- cumtime累积调用时间，与tottime相反，它包含了自己内部调用函数的时间

## 可视化
将得到的prof文件可视化
### gprof2dot
~~~bash
# 生成一张调用关系图
brew install graphviz
poetry add gprof2dot --dev

gprof2dot -f pstats test.prof | dot -Tpng -o test.png
~~~

### RunSnakeRun
~~~bash
# 基于wxpython的交互式可视化，没太看懂
peotry add wxpthon=4.0.7
poetry add RunSnakeRun --dev

runsnake test.prof
~~~

### pyprof2calltree 
~~~bash
# Linux上老牌的性能分析工具
brew install qcachegrind 
poetry add pyprof2calltree --dev

pyprof2calltree -i test.prof -k
~~~
### snakeviz
~~~python
# 基于浏览器，可交互，类似trace耗时，意外的好用，不需要额外依赖
poetry add snakeviz --dev
snakeviz test.prof
## brew问题
~~~bash
sudo rm -rf /Library/Developer/CommandLineTools
sudo xcode-select --switch /Applications/Xcode.app
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
~~~

# memory_profiler
## 使用
~~~python
from memory_profiler import profile

# stream是获取log文件，log文件中记录了每一行的内存变化，似乎只能记录主进程的，没啥用
profile(precision=4, stream=open('test.dat', 'w+'))
def run():
    pass
~~~

~~~bash
poetry add memory_profiler --dev

# 1. 获取结果
mprof run --multiprocess .\test.py  # 获得结果文件（内存随时间的变化） 多进程分别存
mprof run --include-children .\test.py # 有一条线表示所有的
# 保存为：mprofile_20220703013709.dat

# 2. 画图，可以根据结果自己画，也可以用mprof的
mprof plot -t 'Memory Usage'  # 搜索最新的结果文件并画图，基于matplotlib，-t指定图片标题
~~~
