

import sys
import re
from datetime import datetime, date

from content_extraction.extractor import Extractor
from content_extraction.elements import Post, Quote, Profile

class ShavemyfaceForumExtractor(Extractor):
    """Extract posts and profiles from www.shavemyface.com/forum"""

    def extract_from_soup(self, soup, filename=None, relative_filename=None):
        """Extract content from a parsed file from the menessentials.com forum"""
        
        if re.search(r'viewtopic.php\?', filename):
            return self.extract_posts(soup, filename)
        elif re.search('profile.php\?.*mode=viewprofile', filename):
            return self.extract_profile(soup, filename)



    def extract_posts(self, soup, filename):
        """Extract posts"""
     
        # Forum and topic info will be the same for all posts
        forum = soup.find('a', 'nav', href=re.compile('^viewforum.php\?'))
        forum_url = forum['href']
        forum_id = re.search('\Wf=(\d+)', forum_url).group(1)
        forum_name = self.get_text(forum)
        
        topic = soup.find('a', 'maintitle', href=re.compile('^viewtopic.php\?'))
        topic_name = topic.string
        topic_url = topic['href']
        topic_id = re.search('\Wt=(\d+)', topic_url).group(1)

        def new_post():    
            post = Post()
            post.site_name = 'shavemyface'
            post.forum_url = forum_url
            post.forum_id = forum_id
            post.forum_name = forum_name
            post.topic_name = topic_name
            post.topic_id = topic_id
            return post
            
        posts = []
        messages = soup.findAll('span', 'postbody')
        for msg in messages:
        
            # ignore empty spans (or spans already used; see below)
            if not msg.contents:
                continue
                
            # check that this is not a quote
            if msg.parent.get('class', None) == 'quote':
                continue
            
            post = new_post()
            posts.append(post)        
            
            # Extract date and subject
            details = msg.parent.parent.parent.find('span', 'postdetails')
            date = details.find(text=re.compile('Posted: .*'))
            post.date = datetime.strptime(date.string, "Posted: %a %b %d, %Y %I:%M %p")
            subject = details.find(text=re.compile('Post subject: .*'))
            post.subject = re.sub(r'.*Post subject: ', '', subject.string)
            
            # Extract user name and id
            container = msg.parent.parent.parent.parent.parent
            post.user_name = container.td.find('span', 'name').b.string
            post_footer = container.findNextSiblings('tr', limit=1)[0]
            user_link = post_footer.find('a', href=re.compile(r'^profile.php\?'))
            if user_link:
                post.user_url = user_link['href'] 
                post.user_id = re.search(r'profile.php\?.*\bu=(\d+)', post.user_url).group(1)
            
            # Extract quotes
            quotes = msg.parent.findAll('td', 'quote')
            if not quotes: quotes = []
            for quote in reversed(quotes):  # reverse elements, so that quotes will come out in the correct order
                container = quote.parent.parent
                container.extract()
                q = Quote()
                q.text = self.get_text(quote)
                quote_user = container.find('span', 'genmed').b.string
                q.user_name = re.sub('\s*wrote:$', '', quote_user)
                if hasattr(post, 'quote'):
                    post.quote.append(q)
                else:
                    post.quote = [q]
            
            
            # Extract post content and links
            
            # All span.postbody siblings constitute post content
            spans = msg.parent.findAll('span', 'postbody')
            post.text = '\n'.join([self.get_text(span) for span in spans])
            
            # Extract links
            post.link = []
            for span in spans:
                for link in span.findAll('a', href=True):
                        post.link.append(link['href'])
                
            
            # Empty spans that we've used
            for span in spans: 
                span.contents = [] 
            
                    

        print >>sys.stderr, '    ', len(posts), 'posts'
        return posts


    def extract_profile(self, soup, filename):
        """Extract user's profile"""

        profile = Profile()
        profile.site_name = 'shavemyface'
        
        profile.user_id = re.search('\Wu=(\d+)', filename).group(1)
        name = soup.find('th', 'thHead')
        profile.user_name = re.search('Viewing profile :: (.*)', name.string).group(1)
        
        avatar_img = soup.find('img', src=re.compile(r'^images/avatars/'))
        if avatar_img:
            profile.avatar_url = avatar_img['src']
        
        # Extract user attributes
        for attr in soup.findAll('span', 'gen'):
            if attr.parent.name != 'td': continue
            
            nodes = attr.parent.findNextSiblings('td', limit=1)
            if not nodes: continue
            
            value = nodes[0].find('span', 'gen')
            if not value: continue
            
            if attr.string == 'Joined:&nbsp;':
                profile.join_date = datetime.strptime(value.string, '%d %b %Y').date()
            elif attr.string == 'Location:&nbsp;':
                profile.location = value.string
            elif attr.string == 'Occupation:&nbsp;':
                profile.occupation = value.string
            elif attr.string == 'Interests:&nbsp;':
                profile.interests = value.string
            
        print >>sys.stderr, '    profile for', profile.user_name
        
        return profile


extractor = ShavemyfaceForumExtractor

