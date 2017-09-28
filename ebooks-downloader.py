#!/usr/bin/env python3
import re
import lxml.html
import requests
import sys
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter

CHAPTERS_DIR = 'chapters'
TEMPLATE_DIR = 'template'
HEADER_FILE = 'header.tex'
FONT_TEMPLATE = 'fontssetting_template.tex'
FONT_FILE = 'fontssetting.tex'
ZH_FONT = 'PingFang SC'
EN_MAIN_FONT = 'Times New Roman'
EN_SANS_FONT = 'Helvetica'
MAX_RETRY = 3
TIMEOUT = 30
SPECIAL_CHARS = '\\#$%&^_{}~[]\u1680\u180e\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u202f\u205f\ufeff\u3000'
REPLACE_LIST = {
        '#': '\\#',
        '$': '\\$',
        '%': '\\%',
        '&': '\\&',
        '\\': '\\textbackslash ',
        #skip xelatex package fontspec EU1 encoding bug
        #'^': '\\textcircumflex ',
        '^': '',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '[': '【',
        ']': '】',
        '~': '\\textasciitilde ',
        '\u1680': ' ',
        '\u180e': ' ',
        '\u2000': ' ',
        '\u2001': ' ',
        '\u2002': ' ',
        '\u2003': ' ',
        '\u2004': ' ',
        '\u2005': ' ',
        '\u2006': ' ',
        '\u2007': ' ',
        '\u2008': ' ',
        '\u2009': ' ',
        '\u200a': ' ',
        '\u200b': ' ',
        '\u202f': ' ',
        '\u205f': ' ',
        '\u3000': ' ',
        '\ufeff': ' '
        }


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
        for char in SPECIAL_CHARS:
            name = name.replace(char, REPLACE_LIST[char])
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
            for char in SPECIAL_CHARS:
                line = line.replace(char, REPLACE_LIST[char])
            line = re.sub('^\s+', '', line)
            line = re.sub('[\uff00-\uffff]', '', line)
            if not line:
                continue
            f.write(line)
            f.write("\\\\\n")

def get_book(book_url):
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=MAX_RETRY))
    book_meta = get_index(book_url)
    with open("{}/{}".format(TEMPLATE_DIR, FONT_TEMPLATE), 'r') as template, open("{}/{}".format(TEMPLATE_DIR, FONT_FILE), 'w', encoding='utf8') as f:
        for line in template:
            line = re.sub('#zhfont#', ZH_FONT, line)
            line = re.sub('#enmainfont#', EN_MAIN_FONT, line)
            line = re.sub('#ensansfont#', EN_SANS_FONT, line)
            f.write(line)

    with open("{}.tex".format(book_meta['name']), 'w', encoding='utf8') as f:

        f.write("\\input{%s/%s}\n" % (TEMPLATE_DIR, HEADER_FILE))
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
