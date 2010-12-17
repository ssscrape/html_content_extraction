"""Data extractor for www.menessentials.com/forum"""

import sys
import re
from datetime import datetime, date

from content_extraction.extractor import Extractor
from content_extraction.elements import Post, Quote, Profile


class MenessentialsForumExtractor(Extractor):
    """Extract posts and profiles from www.menessentials.com/forum"""

    def extract_from_soup(self, soup, filename=None, relative_filename=None):
        """Extract content from a parsed file from the menessentials.com forum"""
        
        if re.search(r'viewtopic.php\?', filename):
            return self.extract_posts(soup, filename)
        elif re.search('profile.php\?.*mode=viewprofile', filename):
            return self.extract_profile(soup, filename)


    def extract_posts(self, soup, filename):
        """Extract posts"""

        forum = soup.find('td', 'navbar-links').find('a', {'href': re.compile('^viewforum.php\?.*')})
        forum_url = forum['href']
        forum_id = re.search('(\d+)', forum_url).group(1)
        forum_name = self.get_text(forum)
        
        topic = soup.find('td', 'content content-navbar').table.find('span', 'gen').a
        topic_name = topic.b.string
        topic_url = topic['href']
        topic_id = re.search('viewtopic.php.*\Wt=(\d+)', topic_url).group(1)
        
        posts = []
        messages = soup.findAll('div', 'postbody')
        for msg in messages:
            post = Post()
            posts.append(post)        
            
            post.site_name = 'menessentials'
            post.forum_url = forum_url
            post.forum_id = forum_id
            post.forum_name = forum_name
            post.topic_name = topic_name
            post.topic_id = topic_id
            
            date = msg.parent.find('span', 'postdate')
            post.date = datetime.strptime(self.get_text(date), "Posted: %a %b %d, %Y %I:%M %p")
            
            user = msg.parent.parent.find('span', 'name').a
            if user:
                post.user_name = user.string
                post.user_url = user["href"]
                post.user_id = re.search('u=(\d+)', post.user_url).group(1)
            
            post.quote = []
            for quote in reversed(msg.findAll('table', 'quote')):  # Reverse, to handle nested quotes
                quote.extract()
                q = Quote()
                q.text = self.get_text(quote.find('td', 'quote'))
                quote_user = self.get_text(quote.find('td', 'quote_user'))
                q.user_name = re.sub('\s*wrote:$', '', quote_user)
                post.quote.append(q)
            
            # Now, after quotes are removed, we can extract the text of the post         
            post.text = self.get_text(msg)
            
            # Extract links
            post.link = []
            for link in msg.findAll('a', href=True):
                    post.link.append(link['href'])
                
            

        print >>sys.stderr, '    ', len(posts), 'posts'
        return posts


    def extract_profile(self, soup, filename):
        """Extract user's profile"""

        profile = Profile()
        profile.site_name = 'menessentials'            
        
        profile.user_id = re.search('\Wu=(\d+)', filename).group(1)
        name = soup.find('td', 'navbar-links').find('a', {'href': '#'})
        profile.user_name = re.search('Viewing profile :: (.*)', name.string).group(1)
        
        avatar_descr = soup.find('span', 'postdetails')
        if avatar_descr:
            if avatar_descr.string:
                profile.avatar_descr = avatar_descr.string
            avatar = avatar_descr.parent.find('img')
            if avatar and avatar['src']:
                profile.avatar_url = avatar['src']
        
        span = soup.find(text='Joined:&nbsp;')
        date = span.parent.parent.findNextSiblings('td')[0]
        profile.join_date = datetime.strptime(self.get_text(date), '%d %b %Y').date()
        
        span = soup.find(text='Location:&nbsp;')
        profile.location = self.get_text(span.parent.parent.findNextSiblings('td')[0])
        
        span = soup.find(text='Occupation:&nbsp;')
        profile.occupation = self.get_text(span.parent.parent.findNextSiblings('td')[0])
        
        span = soup.find(text='Interests:&nbsp;')
        profile.interests = self.get_text(span.parent.parent.findNextSiblings('td')[0])
        
        print >>sys.stderr, '    profile for', profile.user_name
        
        return profile



extractor = MenessentialsForumExtractor
