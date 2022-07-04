# 1. easyocr
- 精度高，识别慢
~~~python
# pip install easyocr
import easyocr

reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
result = reader.readtext(path, detail=0)
~~~

# 2. pyteeseract
- 精度低，识别快（手写支持很差）
~~~python
# 1. 安装tesseract（下载并设置环境变量）
#  win: https://github.com/UB-Mannheim/tesseract/wiki 
#  mac: brew install tesseract
# 2. 下载语言包：https://github.com/tesseract-ocr/tessdata/blob/main/chi_sim.traineddata
# 2. pip install pytesseract
import pytesseract
from PIL import Image

# win需要额外加一行
pytesseract.pytesseract.tesseract_cmd = ''  # 指定tesseract.exe的路径
text = pytesseract.image_to_string(Image.open(path), lang="chi_sim")
~~~

# 3. PaddleOCR
~~~python
# pip install paddlepaddle
# pip install shapely
# pip install paddleocr
ocr = PaddleOCR(use_angle_cls=True, lang="ch")
result = ocr.ocr(path, cls=True)
for line in result:
    print(line)

# 补充代码生成一张图片，原图在左，文字在右
from PIL import Image
image = Image.open(path).convert("RGB")
boxes = [line[0] for line in result]
txts = [line[1][0] for line in result]
scores = [line[1][1] for line in result]
im_show = draw_ocr(image, boxes, txts, scores)
im_show = Image.fromarray(im_show)
im_show.show()
~~~

# 4. 验证码专用：muggle_ocr
~~~python
# pip install muggle_ocr
import muggle_ocr

sdk = muggle_ocr.SDK(model_type=muggle_ocr.ModelType.Captcha)
with open(path, "rb") as f:
    img = f.read()
text = sdk.predict(image_bytes=img)
print(text)
~~~

# 5. 验证码专用：dddd_ocr（常规数字和字母）
~~~python
# pip install dddd_ocr
import ddddocr
ocr = ddddocr.DdddOcr()

with open(path, "rb") as f:
    img = f.read()
text = ocr.classification(img)
print(text)
~~~
