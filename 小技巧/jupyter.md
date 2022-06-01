# 1. notebook操作
- 参考：https://gist.github.com/fperez/9716279
## 1.1 创建notebook
~~~python
import nbformat as nbf
nb = nbf.v4.new_notebook()

text = """\
# My first automatic Jupyter Notebook
This is an auto-generated notebook."""

code = """\
%pylab inline
hist(normal(size=2000), bins=50);"""

nb['cells'] = [nbf.v4.new_markdown_cell(text),
            nbf.v4.new_code_cell(code) ]
nbf.write(nb, 'test.ipynb')


~~~
## 修改notebook
~~~python
import json
with open("test.ipynb") as f:
    res = json.loads(f.read())["cells"]
res[0]["source"].insert("import numpy as np\n")

with open("test.ipynb", "w") as f:
    f.write(json.dumps(res))
~~~
## 执行notebook
~~~bash
jupyter nbconvert --execute --inplace test.ipynb
~~~

## 执行部分cell
~~~python
from IPython.display import Javascript
Javascript("Jupyter.notebook.execute_cell_range(10,20)") 


Javascript("Jupyter.notebook.execute_cells([2])")

%%javascript
Jupyter.notebook.execute_cells([0]) # 0 to run first cell in notebook etc.

var output_area = this;
// find my cell element
var cell_element = output_area.element.parents('.cell');
// which cell is it?
var cell_idx = Jupyter.notebook.get_cell_elements().index(cell_element);
Jupyter.notebook.execute_cells([cell_idx+1]) # execute next cell

display(Javascript('IPython.notebook.execute_cell_range(IPython.notebook.get_selected_index()+1, IPython.notebook.get_selected_index()+2)'))
~~~

# 2. cell操作
## 2.1 捕获输出
### 2.1.1 CaptureIO对象
- 通过 %%capture output 将单元格的输出捕获成一个CaptureIO对象
- .stdout属性和 .outputs属性
- .stdout属性获取print类型的输出
- .outputs属性获取富文本输出
~~~python
%%capture output
for i in ["a", "b", "c"]:
    print(i)
~~~
~~~python
# 输出全部：重放输出
output()  # 等价于output.show()

# 获取标准输出：通过print进行的输出
output1.stdout

# 获取富文本输出列表：
output.outputs  # RichOutput列表
~~~

### 2.1.2 RichOutput对象
- 由CaptureIO对象的outputs属性而来，是一个列表
- ._repr_html_()   ._repr_xx_() 方法
- .data属性获取一个字典
~~~python
# 图片
output.outputs[0].data
>>> {'text/plain': '<Figure size 1728x648 with 18 Axes>', "image/png": base64}
import base64
with open('001.png', 'wb') as f:
      f.write(base64.b64decode(output1.outputs[1].data["image/png"]))

# 表格
output.outputs[1].data
>>> "{'text/plain': 一行行的数据, "text/html": html表示的df}
pd.read_html(output1.outputs[0].data["text/html"])[0]  
# 注意，转成的df会多一列：【Unnamed: 0】  是序号列
~~~
### 2.1.3 自定义捕获
- [参考链接](https://discourse.jupyter.org/t/cell-magic-to-save-image-output-as-a-png-file/11906/5)
#### 2.1.3.1 示例1
~~~python
from base64 import b64decode
from io import BytesIO

from IPython import get_ipython
from IPython.core.magic import register_cell_magic
import PIL


@register_cell_magic
def capture_png(line, cell):
    get_ipython().run_cell_magic(
        'capture',
        ' --no-stderr --no-stdout result',
        cell
    )
    out_paths = line.strip().split(' ')
    for output in result.outputs:
        data = output.data
        if 'image/png' in data:
            path = out_paths.pop(0)
            if not path:
                raise ValueError('Too few paths given!')
            png_bytes = data['image/png']
            if isinstance(png_bytes, str):
                png_bytes = b64decode(png_bytes)
            assert isinstance(png_bytes, bytes)
            bytes_io = BytesIO(png_bytes)
            image = PIL.Image.open(bytes_io)
            image.save(path, 'png')
~~~
~~~python
%%capture_png test_copy.png hist.png
from IPython.display import Image
from pandas import Series

display(Image('test.png'))
Series([1, 2, 2, 3, 3, 3]).hist()
~~~
### 2.3.2 示例2
~~~python
from base64 import b64decode
from io import BytesIO
import matplotlib.pyplot as plt
import PIL
from IPython import get_ipython
from IPython.core import magic_arguments
from IPython.core.magic import (Magics, cell_magic, magics_class)
from IPython.display import display
from IPython.utils.capture import capture_output


@magics_class
class MyMagic(Magics):

    @cell_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        "--path",
        "-p",
        default=None,
        help=("The path where the image will be saved to. When there is more then one image, multiple paths have to be defined"),
    )
    @magic_arguments.argument(
        "--compression",
        "-c",
        default=None,
        help=("Defines the amout of compression,  quality can be from 0.1 - 100 , images must be .jpg"),
    )
    def polaroid_camera(self, line, cell):
        args = magic_arguments.parse_argstring(MyMagic.polaroid_camera, line)
        paths = args.path.strip('"').split(' ')
        with capture_output(stdout=False, stderr=False, display=True) as result:
            self.shell.run_cell(cell) # thanks @krassowski for this idea!

        for output in result.outputs:
            display(output)
            data = output.data
            if 'image/png' in data:
                path = paths.pop(0)
                if not path:
                    raise ValueError('Too few paths given!')
                png_bytes = data['image/png']
                if isinstance(png_bytes, str):
                    png_bytes = b64decode(png_bytes)
                assert isinstance(png_bytes, bytes)
                bytes_io = BytesIO(png_bytes)
                img = PIL.Image.open(bytes_io)
                if args.compression:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(path, "JPEG", optimize=True,
                             quality=int(args.compression))
                else:
                    img.save(path, 'png')


ipy = get_ipython()
ipy.register_magics(MyMagic)
~~~

~~~python
%%polaroid_camera --path "foo.jpg bar.jpg" --compression 50
plt.plot([1,2],[10,20], color = "r")
plt.show()
plt.plot([3,4],[-10,-20],color = "r")
plt.show()
~~~

# 3. 变量操作
## 3.1 导出变量
~~~python
%store output1
~~~

## 3.2 导入变量
~~~python
%store -r output1
~~~