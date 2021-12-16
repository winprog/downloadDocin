import requests
from fpdf import FPDF
from PIL import Image
from lxml import etree
import re, time, random, os
from joblib import Parallel, delayed
import multiprocessing
import img2pdf

# 图片保存格式
PAGE_IMAGE_EXT = ".jpg"

def getTiltleUrl(originUrl):
	# 获取资料的标题和通用的url链接
	html = etree.HTML(requests.get(originUrl).text)
	theHTML = etree.tostring(html).decode('utf-8')
	# print(theHTML)
	try:
		title = html.xpath('//span[@class="doc_title fs_c_76"]/text()')[0]
	except:
		title = html.xpath('//title/text()')
	fileId = re.findall('\-\d+\.',originUrl)[0][1:-1]

	sid = re.findall('flash_param_hzq:\"[\w\*\-]+\"', theHTML)[0][17:-1]
	url = 'https://docimg1.docin.com/docinpic.jsp?file=' + fileId + '&width=1000&sid=' + sid + '&pcimg=1&pageno='
	return title, url

def getPicture(headers, theurl, pagenum, path):
	# 获取单张图片。成功返回True，否则返回False。
	# time.sleep(3*random.random())
	print('Downloading picture ' + str(pagenum))
	url = theurl + str(pagenum)
	img_req = requests.get(url=url, headers=headers)
	if img_req.content==b'sid error or Invalid!':
		print('Downloading picture ' + str(pagenum) + ' failed, and it may be the end page.')
		return False

	file_name = os.path.join(path, str(pagenum) + PAGE_IMAGE_EXT)
	f = open(file_name, 'wb')
	f.write(img_req.content)
	f.close()

	# 将图片保存为标准格式
	# PIL img P mode can't be save as jpg.
	im = Image.open(file_name)
	if im.mode == "P":
		im = im.convert("RGB")

	im.save(file_name)
	print('picture ' + str(pagenum) + ' is downloaded.')
	return True

def getPictures(theurl, path):
	# 获取图片
	pagenum = 1
	headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36"
	}

	allNum = 0
	num_cores = multiprocessing.cpu_count()

	# don't make too much download threads.
	# It seemed that only two threads are allowed by docin.
	max_download_thread_count = 2
	if num_cores > max_download_thread_count:
		num_cores = max_download_thread_count 
	download_more = True
	start = 1
	while download_more:
		results = Parallel(n_jobs=num_cores)(delayed(getPicture)(headers, theurl, pagenum, path) for pagenum in range(start, start + num_cores))
		oknum = sum(1 for result in results if result)
		start += oknum
		allNum += oknum
		download_more = oknum == num_cores 
	return allNum

def combinePictures2Pdf(path, pdfName, allNum):
	# 合并图片为pdf
	print('Start combining the pictures...')
	pagenum = 1
	file_name = os.path.join(path, str(pagenum) + PAGE_IMAGE_EXT)
	cover = Image.open(file_name)
	width, height = cover.size
	cover.close()
	pdf = FPDF(unit = "pt", format = [width, height])
	while allNum>=pagenum:
		try:
			print('combining picture ' + str(pagenum))
			file_name = os.path.join(path, str(pagenum) + PAGE_IMAGE_EXT)
			pdf.add_page()
			pdf.image(file_name, 0, 0)
			pagenum += 1
		except Exception as e:
			print(e)
			break;
	pdf.output(pdfName, "F")
	pdf.close()

def combinePictures2Pdf2(path, pdfName, allNum):
	# 合并图片为pdf
	print('Start combining the pictures...')
	pagenum = 1
	file_name = os.path.join(path, str(pagenum) + PAGE_IMAGE_EXT)
	cover = Image.open(file_name)
	width, height = cover.size
	cover.close()

	filename = pdfName
	images = [os.path.join(path, str(pagenum)+PAGE_IMAGE_EXT) for pagenum in range(1, allNum)]
	with open(filename, "wb") as f:
		f.write(img2pdf.convert(images))
	

def removePictures(path, allNum):
	# 删除原图片
	pagenum = 1
	while allNum>=pagenum:
		try:
			print('deleting picture ' + str(pagenum))
			file_name = os.path.join(path, str(pagenum) + PAGE_IMAGE_EXT)
			os.remove(file_name)
			pagenum += 1
		except Exception as e:
			print(e)
			break;

if __name__ == '__main__':
	# 文件存储的路径
	path =os.path.abspath(os.path.curdir)
	# 需要的资料的网址
	# originUrl = 'https://www.docin.com/p-977106193.html?docfrom=rrela'
	originUrl = input('input the url: ')
	result = getTiltleUrl(originUrl)
	# title = result[0].split('.')[0]
	title = result[0][0]
	url = result[1]
	print(title, url)
	allNum = getPictures(url, path)
	pdfName = os.path.join(path, title + '.pdf')
	# combinePictures2Pdf(path, pdfName, allNum)
	combinePictures2Pdf2(path, pdfName, allNum)
	removePictures(path, allNum)
