# This is a sample Python script.

import os
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal, LAParams
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfpage import PDFPage
import re

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


def getFileName(filepath):
    file_list = []
    for root, dirs, files in os.walk(filepath):
        for filespath in files:
            if 'pdf' in filespath.split('.')[1]:
                file_list.append(os.path.join(root, filespath))
    return file_list


def generate_author(author):
    # 过滤掉作者名后面的各种符号，并生成引用的格式
    # print(author)
    author = re.sub('by |[\s\d\*∗\/@†\(\&\)]+$', '', author)
    author_list = re.split('\s+', author)
    author_str = author_list[len(author_list) - 1]
    for i in range(0, len(author_list) - 1):
        author_str = author_str + ' ' + author_list[i][0]
    return author_str


def parse(DataIO, save_path):
    # 用文件对象创建一个PDF文档分析器
    parser = PDFParser(DataIO)
    # 创建一个PDF文档
    doc = PDFDocument(parser)
    # 分析器和文档相互连接
    parser.set_document(doc)
    # 检查文档是否可以转成TXT，如果不可以就忽略
    if not doc.is_extractable:
        raise PDFTextExtractionNotAllowed
    else:
        # 创建PDF资源管理器，来管理共享资源
        rsrcmagr = PDFResourceManager()
        # 创建一个PDF设备对象
        laparams = LAParams()
        # 将资源管理器和设备对象聚合
        device = PDFPageAggregator(rsrcmagr, laparams=laparams)
        # 创建一个PDF解释器对象
        interpreter = PDFPageInterpreter(rsrcmagr, device)
        last_para = ''  # 记录上一段文本
        count = 0  # 对文本块进行计数，方便后续查找标题和作者
        author = ''  # 记录作者
        ab_count = 0  # 记录已识别的摘要的数量，避免提取文中的abstract

        # 循环遍历列表，每次处理一个page内容
        for page in enumerate(PDFPage.create_pages(doc)):
            interpreter.process_page(page[1])
            # 接收该页面的LTPage对象
            layout = device.get_result()
            # 这里的layout是一个LTPage对象 里面存放着page解析出来的各种对象
            # 一般包括LTTextBox，LTFigure，LTImage，LTTextBoxHorizontal等等一些对像
            # 想要获取文本就得获取对象的text属性
            for x in layout:
                try:
                    if isinstance(x, LTTextBoxHorizontal):
                        with open('%s' % save_path, 'a', encoding='utf-8') as f:
                            result = x.get_text()  # 每块的内容
                            # print(result)
                            # 提取标题
                            if count == 0:
                                # 如果是researchgate的文章，直接翻页
                                if re.findall('^see discussions', result.lower()):
                                    break
                                # 如果第一行是各种页眉等干扰信息，直接略过
                                if re.findall(
                                        '(^[0-9])|(^(research )?article)|(unclassified)|(www.)|(accepted (from|manuscript))|(proceedings of)|(vol.)|(volume \d)|(https?://)|(^ieee)|(sciencedirect)|(\d{4}\)$)|(\d{1,4} – \d{1,4}$)|(cid:)',
                                        re.split('\s+$', result.lower())[0]) != [] or '':
                                    count -= 1
                                else:
                                    # 将结果写入TXT
                                    f.write('\n' + result.replace('\n', '') + '\n')
                            # 提取作者
                            elif count == 1:
                                # 只取第一作者
                                author = result.split('\n')[0].split(',')[0].split(' and ')[0]
                                author = generate_author(author)
                                print('author ' + author)
                            # 去掉pdf文件读取的各种换行符
                            result = result.replace('\n', '')
                            try:
                                # 转为小写，去掉空格，方便正则识别
                                last_para = last_para.lower().replace(' ', '')
                                # print(result)
                                # 匹配Abstract和摘要内容分开的情况
                                if re.findall('abstract$', last_para) != []:
                                    # 去掉关键词
                                    oringin_result = re.split('(K|k)(eyword|EYWORD)[sS]?', result)[0]
                                    write_cont = author + '等人提出：' + oringin_result + '\n'
                                    ab_count += 1
                                    f.write(write_cont)
                                # 匹配Abstract和摘要内容位于同一行的情况
                                elif re.findall('^abstract', result.lower().replace(' ', '')) != [] and re.findall(
                                        'abstract$', result.lower().replace(' ', '')) == []:
                                    # 确保摘要只匹配一次，不匹配文中的Abstract字眼
                                    if ab_count == 0:
                                        # 去掉Abstract字眼及其后续的符号
                                        oringin_result = re.sub('(a|A)(bstract|BSTRACT)[- —.]?', '', result)
                                        # 去掉关键词
                                        oringin_result = re.split('(K|k)(eyword|EYWORD)[sS]?', oringin_result)[0]
                                        # 组织语言写入TXT
                                        write_cont = author + '等人提出：' + oringin_result + '\n'
                                        ab_count += 1
                                        f.write(write_cont)
                                # 匹配结论
                                elif re.findall('(^(i|v|x|\d)*\.?conclusions?)|(conclusions?$)', last_para) != []:
                                    # 避免因图表在标题下方导致的识别错误
                                    if re.findall('^fig', result.lower()):
                                        continue
                                    # 写入TXT
                                    f.write(write_cont)
                            except Exception as e:
                                print(e)
                            last_para = result
                            count += 1
                except Exception as e:
                    print('out' + str(e))
            else:
                continue
        with open('%s' % save_path, 'a', encoding='utf-8') as f:
            f.write('\n')



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # 解析本地PDF文本，保存到本地TXT
    folder = '/Users/KoKei/PycharmProjects/PDF_Reader/data'  # 需要读取pdf的文件夹的路径，注意为绝对路径
    write_txt_file = '/result.txt'  # 保存结果的文件，为txt文件
    success_count = 0  # 统计成功的次数
    fail_count = 0  # 统计失败的次数

    # 单次调用，供开发测试
    # pdf_filename = folder + '/teat.pdf'
    # with open(pdf_filename, 'rb') as pdf_html:
    #     try:
    #         parse(pdf_html, folder + write_txt_file)
    #         success_count += 1
    #     except Exception as e:
    #         print(e)
    #         fail_count += 1

    pdf_list = getFileName(folder)
    # # 依次读取元祖，获取pdf文件位置
    for file_item in pdf_list:
        with open(file_item, 'rb') as pdf_html:
            try:
                parse(pdf_html, folder + write_txt_file)
                success_count += 1
            except Exception as e:
                # 文件读取或翻译失败则将错误信息写入TXT
                print('文档读取失败：' + str(e) + '，路径为：' + file_item)
                with open('%s' % (folder + write_txt_file), 'a', encoding='utf-8') as f:
                    f.write('\n' + '文档读取失败：' + str(e) + '，路径为：' + file_item + '\n')
                fail_count += 1

    print('共读取pdf文件' + str(success_count + fail_count) + '个，其中成功读取' + str(
        success_count) + '个，失败' + str(fail_count) + '个')
