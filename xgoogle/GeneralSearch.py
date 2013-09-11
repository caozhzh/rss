#!/usr/bin/python
# encoding: utf-8
#
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# http://www.catonmat.net/blog/python-library-for-google-search/
#
# Code is licensed under MIT license.
#
# caozhzh@gmail.com
# try make general search for multi search engine
#

import re
import urllib
from htmlentitydefs import name2codepoint
from BeautifulSoup import BeautifulSoup

### ini handler
import ConfigParser
import string, sys

import ast

from browser import Browser, BrowserError

class GeneralSearchError(Exception):
    """
    Base class for General Search exceptions.
    """
    pass

class GeneralParseError(GeneralSearchError):
    """
    Parse error in General results.
    self.msg attribute contains explanation why parsing failed
    self.tag attribute contains BeautifulSoup object with the most relevant tag that failed to parse
    Thrown only in debug mode
    """
     
    def __init__(self, msg, tag):
        self.msg = msg
        self.tag = tag

    def __str__(self):
        return self.msg

    def html(self):
        return self.tag.prettify()

class GeneralSearchResult:
    def __init__(self, title, url, desc):
        self.title = title
        self.url = url
        self.desc = desc

    def __str__(self):
        return 'General Search Result: "%s"' % self.title

class GeneralSearch(object):
    def __init__(self, query, engine="google", conf="", random_agent=True, debug=False, lang="en", tld="com.hk", re_search_strings=None):

        # read ini
        self.cf = ConfigParser.RawConfigParser()
        self.conf = conf
        self.cf.read( self.conf )

        self.query = query
        self.debug = debug
        self.engine = engine
        self.browser = Browser(debug=debug)
        self.results_info = None
        self.eor = False # end of results
        self._page = 0
        self._first_indexed_in_previous = None
        self._filetype = None
        self._last_search_url = None
        self._results_per_page = self.cf.getint(self.engine, "page_nums")
        self._last_from = 0
        self._lang = lang
        self._tld = tld
        self._encoding = 'utf8'

        try:
            self._encoding = self.cf.get(self.engine, "encoding")
        except Exception, e:
            pass
        else:
            pass
        finally:
            pass

        #print self._encoding
        self.query = self.query.encode(self._encoding, 'ignore')

        if re_search_strings:
            self._re_search_strings = re_search_strings
        elif lang == "de":
            self._re_search_strings = ("Ergebnisse", "von", u"ungefähr")
        elif lang == "es":
            self._re_search_strings = ("Resultados", "de", "aproximadamente")
        elif lang == "fr":
            self._re_search_strings = ("résultats", "de", "Environ")
        # add more localised versions here
        else:
            self._re_search_strings = ("Results", "of", "about")

        if random_agent:
            self.browser.set_random_user_agent()

    @property
    def num_results(self):
        if not self.results_info:
            page = self._general_get_results_page()
            total = self._general_extract_total(page)
            if total == 0:
                self.eor = True
        return self.results_info['total']

    @property
    def last_search_url(self):
        return self._last_search_url

    def _get_page(self):
        return self._page

    def _set_page(self, page):
        self._page = page

    page = property(_get_page, _set_page)

    def _get_first_indexed_in_previous(self):
        return self._first_indexed_in_previous

    def _set_first_indexed_in_previous(self, interval):
        if interval == "day":
            self._first_indexed_in_previous = 'd'
        elif interval == "week":
            self._first_indexed_in_previous = 'w'
        elif interval == "month":
            self._first_indexed_in_previous = 'm'
        elif interval == "year":
            self._first_indexed_in_previous = 'y'
        else:
            # a floating point value is a number of months
            try:
                num = float(interval)
            except ValueError:
                raise GeneralSearchError, "Wrong parameter to first_indexed_in_previous: %s" % (str(interval))
            self._first_indexed_in_previous = 'm' + str(interval)
    
    first_indexed_in_previous = property(_get_first_indexed_in_previous, _set_first_indexed_in_previous, doc="possible values: day, week, month, year, or a float value of months")
    
    def _get_filetype(self):
        return self._filetype

    def _set_filetype(self, filetype):
        self._filetype = filetype
    
    filetype = property(_get_filetype, _set_filetype, doc="file extension to search for")
    
    def _get_results_per_page(self):
        return self._results_per_page

    def _set_results_par_page(self, rpp):
        self._results_per_page = rpp

    results_per_page = property(_get_results_per_page, _set_results_par_page)

    def get_results(self):
        """ Gets a page of results """
        if self.eor:
            return []
        MAX_VALUE = 1000000
        page = self._general_get_results_page()

        total = self._general_extract_total(page)
        results = self._general_extract_results(page)

        page.decompose()
        
        search_info = {'from': self.results_per_page*self._page+1,
                       'to': self.results_per_page*self._page + len(results),
                       'total': total}
        if not self.results_info:
            self.results_info = search_info
            if total == 0:
                self.eor = True
                return []
        if not results:
            self.eor = True
            return []
        if self._page > 0 and search_info['from'] == self._last_from:
            self.eor = True
            return []
        if search_info['to'] == search_info['total']:
            self.eor = True
        self._page += 1
        self._last_from = search_info['from']
        return results

    def _maybe_raise(self, cls, *arg):
        if self.debug:
            raise cls(*arg)

    # not used, but some code should be referenced in future
    def _get_results_page_google(self):
        if self._page == 0:
            if self._results_per_page == 10:
                url = self.cf.get(self.engine, "SEARCH_URL_0")
            else:
                url = self.cf.get(self.engine, "SEARCH_URL_1")
        else:
            if self._results_per_page == 10:
                url = self.cf.get(self.engine, "NEXT_PAGE_0")
            else:
                url = self.cf.get(self.engine, "NEXT_PAGE_1")

        safe_url = [url % { 'query': urllib.quote_plus(self.query),
                           'start': self._page * self._results_per_page,
                           'num': self._results_per_page,
                           'tld' : self._tld,
                           'lang' : self._lang }]
        
        # possibly extend url with optional properties
        if self._first_indexed_in_previous:
            safe_url.extend(["&as_qdr=", self._first_indexed_in_previous])
        if self._filetype:
            safe_url.extend(["&as_filetype=", self._filetype])
        
        safe_url = "".join(safe_url)
        self._last_search_url = safe_url
        
        try:
            page = self.browser.get_page(safe_url)
        except BrowserError, e:
            raise GeneralSearchError, "Failed getting %s: %s" % (e.url, e.error)
        return BeautifulSoup(page)

    def _general_get_results_page(self):
        url = self.cf.get(self.engine, "SEARCH_URL")
        page_mode = self.cf.getint(self.engine, "PAGE_MODE")

        if page_mode==1:
            safe_url = [url % { 'query': urllib.quote_plus(self.query),
                               'num': self._page * self._results_per_page }]
        elif page_mode==2:
            safe_url = [url % { 'query': urllib.quote_plus(self.query),
                               'num': self._page + 1 }]
        else:
            safe_url = [url % { 'query': urllib.quote_plus(self.query),
                               'num': self._page + 1 }]
        
        safe_url = "".join(safe_url)
        self._last_search_url = safe_url
        
        print safe_url

        try:
            page = self.browser.get_page(safe_url).decode(self._encoding, 'ignore')
        except BrowserError, e:
            raise GeneralSearchError, "Failed getting %s: %s" % (e.url, e.error)
        return BeautifulSoup(page)

    def _general_extract_total(self, soup):
        total_tag = self.cf.get(self.engine, "total_tag")
        total_tag_filter = self.cf.get(self.engine, "total_tag_filter")
        total_tag_filter = ast.literal_eval(total_tag_filter)

        div_ssb = soup.find(total_tag, total_tag_filter)
        if not div_ssb:
            self._maybe_raise(GeneralParseError, "Span with class:num of results was not found on Baidu search page", soup)
            return 0
        p = div_ssb
        txt = ''.join(p.findAll(text=True))
        txt = txt.replace(',', '')
        txt = txt.replace('&nbsp;', '')
        #matches = re.search(r'(\d+) - (\d+) %s (?:%s )?(\d+)' % self._re_search_strings, txt, re.U)
        #matches = re.search(r'(\d+) %s' % self._re_search_strings[0], txt, re.U|re.I)
        matches = re.search(r'(\d+)', txt, re.U)

        if not matches:
            print self._re_search_strings[0]
            print txt
            return 0
        return int(matches.group(1))

    def _general_extract_results(self, soup):
        result_container_tag = ''
        result_container_tag_filter = {}
        try:
            result_container_tag = self.cf.get(self.engine, "result_container_tag")
            result_container_tag_filter = self.cf.get(self.engine, "result_container_tag_filter")
            result_container_tag_filter = ast.literal_eval(result_container_tag_filter)
        except Exception, e:
            pass
        else:
            pass
        finally:
            pass

        result_tag = self.cf.get(self.engine, "result_tag")
        result_tag_filter = self.cf.get(self.engine, "result_tag_filter")
        result_tag_filter = ast.literal_eval(result_tag_filter)

        title_tag = self.cf.get(self.engine, "title_tag")
        title_tag_filter = self.cf.get(self.engine, "title_tag_filter")
        title_tag_filter = ast.literal_eval(title_tag_filter)

        desc_tag = self.cf.get(self.engine, "desc_tag")
        desc_tag_filter = self.cf.get(self.engine, "desc_tag_filter")
        desc_tag_filter = ast.literal_eval(desc_tag_filter)

        if result_container_tag!='':
            soup = soup.find(result_container_tag, result_container_tag_filter)

        results = soup.findAll(result_tag, result_tag_filter)
        ret_res = []
        for result in results:
            title_a = result.find(title_tag, title_tag_filter)
            if not title_a:
                self._maybe_raise(GeneralParseError, "Title tag in Google search result was not found", result)
                continue

            title = ''.join(title_a.findAll(text=True))
            title = self._html_unescape(title)
            url = title_a['href']
            match = re.match(r'/url\?q=(http[^&]+)&', url)
            if match:
                url = urllib.unquote(match.group(1))

            desc_div = result.find(desc_tag, desc_tag_filter)
            if not desc_div:
                self._maybe_raise(GeneralParseError, "Description tag in Google search result was not found", result)
                continue

            desc_strs = []
            def looper(tag):
                if not tag: return
                for t in tag:
                    try:
                        if t.name == 'br': break
                    except AttributeError:
                        pass

                    try:
                        desc_strs.append(t.string)
                    except AttributeError:
                        desc_strs.append(t)

            looper(desc_div)
            looper(desc_div.find('wbr')) # BeautifulSoup does not self-close <wbr>

            desc = ''.join(s for s in desc_strs if s)
            desc = self._html_unescape(desc)

            if not title or not url or not desc:
                eres = None
            else:
                eres = GeneralSearchResult(title, url, desc)
                
            if eres:
                ret_res.append(eres)
        return ret_res

    def _html_unescape(self, str):
        def entity_replacer(m):
            entity = m.group(1)
            if entity in name2codepoint:
                return unichr(name2codepoint[entity])
            else:
                return m.group(0)

        def ascii_replacer(m):
            cp = int(m.group(1))
            if cp <= 255:
                return unichr(cp)
            else:
                return m.group(0)

        s =    re.sub(r'&#(\d+);',  ascii_replacer, str, re.U)
        return re.sub(r'&([^;]+);', entity_replacer, s, re.U)
        
#class GoogleSearch(GeneralSearch):