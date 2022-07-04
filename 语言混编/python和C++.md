# python中的结构
## 1. 普通结构都是结构体
- int是一个struct对象
~~~c
// int
struct _longobject {
    PyObject_VAR_HEAD  // 统一的头部
    digit ob_digit[1]  // unsigned short 会根据数值的大小动态分配
}

// float
typedef struct {
    PyObject_VAR_HEAD  // 统一的头部
    double ob_fval;  // 一个浮点数是8个字节
}

// bool 和 int一样也是longobject
// False就是0， True就是1
// 结构体对象
struct _longobject _Py_FalseStruct = {
    PyVarObject_HEAD_INIT(&PyBool_Type, 0)
    {0}
}
struct _longobject _Py_TrueStruct = {
    PyVarObject_HEAD_INIT(&PyBool_Type, 1)
    {1}
}

~~~
