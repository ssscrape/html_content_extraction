"""Data extractor for the Russian news site lenta.ru"""

import sys, os
import re
from datetime import datetime, date

from BeautifulSoup import Tag, NavigableString
from content_extraction.extractor import Extractor


class MagazinesRussRuExtractor(Extractor):

    def __init__(self, **kwargs):
        Extractor.__init__(self, **kwargs)
        self.pages = {}
        self.index = None

    def extract_from_soup(self, soup, filename, relative_filename, **kwargs):

         if 'index' in relative_filename:
             self.index = soup
         else:    
             content = soup.find("div", { "class" : "pl" })
             self.pages[relative_filename] = content

         return None

    def finish(self):
        if self.index:
            sections = self.index.findAll("ul")
            for section in sections:
                new_section = Tag(self.index, "div")
                items = section.findAll("li")
                for item in items:
                    link = item.find("a", {"href": True})
                    if link and link["href"] in self.pages:
                        title = Tag(self.index, "h4")
                        title.insert(0, NavigableString(self.get_text(item)))
                        new_section.insert(1000000, title)
                        new_section.insert(1000000, self.pages[link["href"]])
                section.replaceWith(new_section) 
                
            self.fix_russian_encoding(self.index)

            return self.index        


    def fix_russian_encoding(self, node):
        to_replace = []
        for e in node.recursiveChildGenerator():
            if isinstance(e, NavigableString):
                if re.search(u'[\u2320\u25A0\u2248\u2567\u2518]', e):
                    #print >>sys.stderr, e.string.encode("utf-8")
                    s = unicode(e)
                    for old, new in [(u'\u2320', u'\u201d'),(u'\u25A0', u'\u201d'),(u'\u2248', u'\u2014'),(u'\u2567', u'\u2116'),(u'\u2518', u'\u2026')]:
                        s = s.replace(old, new)
                    #print >>sys.stderr, s.encode("utf-8")
                    to_replace.append((e, s))

        for old, new in to_replace:
            old.replaceWith(NavigableString(new))


extractor = MagazinesRussRuExtractor

