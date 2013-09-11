#!/usr/bin/python
#encoding: utf-8

import re
import urllib
from BeautifulSoup import BeautifulSoup
from browser import Browser, BrowserError

class GeneralFetch(object):
    def fetch(self):
        url = "http://blog.sina.com.cn/u/1696709200"
        b = Browser()
        page = b.get_page(url)
        be = BeautifulSoup(page)
        div = be.find('div', {'class': 'diywidget'})
        return div


