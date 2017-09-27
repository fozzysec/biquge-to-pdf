#!/usr/bin/env python3
import re
import lxml.html
import requests
import sys
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter

CHAPTERS_DIR = 'chapters'
ZH_FONT = 'Hiragino Sans GB'
EN_FONT = 'Helvetica'
MAX_RETRY = 3
TIMEOUT = 30

def get_index(book_url):
    response = requests.get(book_url)
    response.encoding='utf8'
    doc = lxml.html.fromstring(response.text)

    site_domain = urlparse(book_url).netloc
    site_domain = 'http://{}'.format(site_domain)
    book_meta = {}
    name = doc.xpath('//meta[@property="og:title"]/@content')[0]
    author = doc.xpath('//meta[@property="og:novel:author"]/@content')[0]
    book_meta['name'] = name
    book_meta['author'] = author

    chapters = []
    chapter_list = doc.xpath('//div[@id="list"]/dl/dd/a')
    for chapter in chapter_list:
        url = chapter.xpath('./@href')[0]
        url = "{}{}".format(site_domain, url)
        name = chapter.xpath('./text()')[0]
        chapter_info = {
                'name': name,
                'url': url
                }
        chapters.append(chapter_info)
    book_meta['chapters'] = chapters
    return book_meta

def get_chapter(session, chapter_id, name, url, retries = 3):
    if(retries <= 0):
        with open("{}/{}.tex".format(CHAPTERS_DIR, chapter_id), 'w', encoding='utf8') as f:
            f.write("\\chapter{%s}\n" % name)
        return
    print("Fetching chapter {}: {}".format(chapter_id, name))
    response = session.get(url, timeout=TIMEOUT)
    response.encoding = 'utf8'
    doc = lxml.html.fromstring(response.text)
    content = doc.xpath('//div[@id="content"]/text()')
    if not content:
        print("Retrying {} on fetching chapter {}".format(retries, name))
        get_chapter(session, chapter_id, name, url, retries-1)
        return
    with open("{}/{}.tex".format(CHAPTERS_DIR, chapter_id), 'w', encoding='utf8') as f:
        f.write("\\chapter{%s}\n" % name)
        if content:
            content[0] = re.sub('\w+\(\);', '', content[0])
        for line in content:
            line = re.sub('[&\^\\\[\]\{\}_\$#@\?\ufeff]', '', line)
            if not line:
                continue
            f.write(line)
            f.write("\\\\\n")

def get_book(book_url):
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=MAX_RETRY))
    book_meta = get_index(book_url)
    with open("{}.tex".format(book_meta['name']), 'w', encoding='utf8') as f:
        f.write("\\documentclass[11pt,a4paper]{book}\n")
        f.write("\\XeTeXlinebreaklocale \"zh\"\n")
        f.write("\\XeTeXlinebreakskip = 0pt plus 1pt minus 0.1pt\n")
        f.write("\\usepackage[top=1in,bottom=1in,left=1.25in,right=1.25in]{geometry}\n")
        f.write("\\usepackage{float}\n")
        f.write("\\usepackage{fontspec}\n")
        f.write("\\newfontfamily\zhfont{%s}\n" % ZH_FONT)
        f.write("\\newfontfamily\zhpunctfont{%s}\n" % ZH_FONT)
        f.write("\\setmainfont{%s}\n" % EN_FONT)
        f.write("\\usepackage{zhspacing}\n")
        f.write("\\zhspacing\n")
        f.write("\\usepackage{hyperref}\n")
        f.write("\\hypersetup{linktoc=all}\n")
        f.write("\\raggedbottom\n")

        f.write("\\title{%s}\n" % book_meta['name'])
        f.write("\\author{%s}\n" % book_meta['author'])
        f.write("\\begin{document}\n")
        f.write("\\maketitle\n")
        f.write("\\tableofcontents\n")
        for i in range(len(book_meta['chapters'])):
            chapter = book_meta['chapters'][i]
            get_chapter(session, i+1, chapter['name'], chapter['url'])
            f.write("\\input{%s/%d.tex}\n" %(CHAPTERS_DIR, i+1))
        f.write("\\end{document}\n")

get_book(sys.argv[1])
