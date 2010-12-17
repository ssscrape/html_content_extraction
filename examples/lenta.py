"""Data extractor for the Russian news site lenta.ru"""

import sys
import re
from datetime import datetime, date

from BeautifulSoup import Tag
from content_extraction.extractor import Extractor


class LentaExtractor(Extractor):



    def extract_from_soup(self, soup, file_name):

        # Find content
        content = soup.find("td", { "class" : "statya" })
        if content:
            # This is an article

            # Find publication date
            date = content.find("table", {'class': None}).find("div", "dt").string
            # In python 2.5: 
            date = datetime.strptime(date, "%d.%m.%Y, %H:%M:%S")
            # In python 2.4: 
            #date = datetime(*(time.strptime(date, "%d.%m.%Y, %H:%M:%S")[0:6]))
            
            date_elt = Tag(soup, "span")
            date_elt['class'] = 'pub_date'
            date_elt['title'] = str(date)
            content.insert(0, date_elt)
            
            # Remove remaining navigation
            for node in content.findAll('table', {'class': [None, 'bottom-menu', 'photo']}) + \
                        content.findAll('div', 'dt'):
                if node:
                    node.extract()
            # Related links: keep only URLs of the links         
            for links_paragraph in content.findAll('p', 'links'):
                links_paragraph.extract()
                for link in links_paragraph.findAll('a', href=True):
                    link['class'] = 'related'
                    if link.string:
                        link['title'] = link.string
                    for child in link.contents: child.extract()
                    content.insert(0, link)
            # Info tab: only extract links to stories/comments
            for node in content.findAll('table', 'vrezka'):
                node.extract()
                for link in node.findAll('a', href=True):
                    link['class'] = 'info'
                    for child in link.contents: child.extract()
                    content.insert(0, link)
        else:
            # this is a story
            content = soup.find("table", { "class" : "line" })

        # Find categories
        header = soup.find('table', 'shapka')
        if header:
            categories = header.find('div', 'h')
            if categories:
                for category in categories.findAll('a', {'href': True}):
                    category['class'] = 'category'
                    for child in category.contents: child.extract()
                    content.insert(0, category)
     
        return content


extractor = LentaExtractor

