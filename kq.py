#!/usr/bin/python
#-*- coding: utf-8 -*-
import os
os.chdir('/home/caozhzh/work/rss')

import re
import urllib
from xgoogle.BeautifulSoup import BeautifulSoup
from xgoogle.browser import Browser, BrowserError
from xgoogle.GeneralFetch import GeneralFetch

url = "http://blog.sina.com.cn/u/1696709200"
b = Browser()
page = b.get_page(url)
page = page.replace('<!–[if lte IE 6]>','')
page = page.replace('<![endif]–>','')
#print page

be = BeautifulSoup(page)
div = be.find('div', {'class': 'diywidget'})
txt = ''.join(div.findAll(text=True))
#print type(txt)

import feedparser
origin_feed = feedparser.parse('http://blog.sina.com.cn/rss/1696709200.xml')

from feedformatter import Feed
import time
import datetime
import uuid

# Create the feed
feed = Feed()

# Set the feed/channel level properties
feed.feed["title"] = u"孔青老师信息公告"
feed.feed["link"] = u"http://blog.sina.com.cn/u/1696709200"
feed.feed["author"] = u"自动获取工具"
feed.feed["description"] = u"此RSS是由自动获取新浪博客信息公告的工具产生的，作者无法保证正确性，请以孔青老师博客公布的信息为准"

import json
lastmd5=""
try:
    with open('lastmd5.txt', 'r') as f:
        lastmd5 = json.load(f)
except:
    pass

notices=[]
try:
    with open('notices.txt', 'r') as f:
        notices = json.load(f)
except:
    pass

import hashlib
md5=hashlib.md5()
md5.update(txt.encode('ascii', 'ignore'))
md5.digest()
#print lastmd5
#print md5.hexdigest()

if lastmd5 != md5.hexdigest() :
    # Create an item
    item = {}
    tm = datetime.datetime.now()
    item["title"] = tm.strftime("%a, %d %b %Y %H:%M:%S %Z") + u"获取到的新信息公告"
    item["link"] = "http://blog.sina.com.cn/u/1696709200"
    item["description"] = txt 
    item["pubDate"] = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %Z')#timetuple
    item["guid"] = str(uuid.uuid3(uuid.NAMESPACE_X500,str(tm)))

    notices.insert(0, item)
    with open('notices.txt', 'a+') as f:
        json.dump( notices, f )

    lastmd5 = md5.hexdigest()
    with open('lastmd5.txt', 'w') as f:
        json.dump(lastmd5, f)

# Add item to feed
# You can do this as many times as you like with multiple items
i = 0
while i < len(notices) :
    feed.items.append(notices[i])
    i = i + 1

i = 0
while ( i < len(origin_feed.entries) ):
    str1=origin_feed.entries[i].published
    str2=re.sub(r"[+-]([0-9])+", "", str1)
    dt = datetime.datetime.strptime(str2, '%a, %d %b %Y %H:%M:%S ')
    tm = dt.timetuple()
    origin_feed.entries[i].published = tm
    origin_feed.entries[i].updated = tm

    feed.items.append(origin_feed.entries[i])
    i = i + 1

# Print the feed to stdout in various formats
#print feed.format_rss1_string()
#print feed.format_rss2_string()
#print feed.format_atom_string()

# Save the feed to a file in various formats
#feed.format_rss1_file("example_feed_rss1.xml")
feed.format_rss2_file("rss2.xml")

import os
cmd = 'cp rss2.xml /var/www'
os.system(cmd)

