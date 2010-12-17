"""HTML page cleanup: model learner and page cleaner"""

import sys
import re
from datetime import datetime, date
#import hashlib
import cPickle
import copy

from BeautifulSoup import NavigableString, Tag

from content_extraction.extractor import Extractor


class CleanupModelLearner(Extractor):
    """Class that learns a model for cleaning up the content of files"""

    def __init__(self, max_duplicates=2, **kwargs):
        """Initialize cleanup model learner.
        
        Takes standard options of Extractor, plus:
         - max_duplicates: maximum number of (near) identical documents in the set
        """
        
        Extractor.__init__(self, **kwargs)
        self.max_duplicates = max_duplicates
        
        ## dictionary of HTML elements (paths and content) with counts 
        self.elements = dict()



    def add_to_model(self, elements):
        for path in elements:
            if path not in self.elements:
                self.elements[path] = elements[path]
            else:
                for text in elements[path]:
                    if text in self.elements[path]:
                        self.elements[path][text] += 1
                    else:
                        self.elements[path][text] = 1
                    
                    
                    
    def get_model(self, format='python'):
        """Returns the computed cleanup model in a specified format.

        - format='python': returns the model as a python dictionary (default)
        - format='pickle': returns the model compressed with cPickle (i.e., a string)
        """

        model = dict()
        for path in self.elements.keys():
             counts = [self.elements[path][text] for text in self.elements[path]]
             repeated_cnt = len([x for x in counts if x > self.max_duplicates])
             if repeated_cnt:
                model[path] = 1.0 * repeated_cnt / len(counts)
        
        if format == 'pickle':        
            return cPickle.dumps(model, -1)
        else:    
            return model
        
    def load_model(self, model):    
        """Load a cleanup model: 'model' is a filename or output of get_model"""

        if isinstance(model, basestring):
            #self.skip_paths = cPickle.load(open(model_file))
            self.skip_paths = eval(open(model).read())
        else:
            self.skip_paths = model    
        
    def signature(self, path, string = ''):
        s = path + string
        #return str(len(s)) + ':' + hashlib.sha1(s.encode("utf-8")).digest()
        return s


    def filename_template(self, filename):
        res = re.sub('!', '', filename, re.UNICODE)
        res = re.sub('\d+', '!', res, re.UNICODE)
        res = re.sub('\w+', 'a', res, re.UNICODE)
        res = re.sub('!', '1', res, re.UNICODE)
        return res

    def extract_from_soup(self, soup, filename, relative_filename):
        self.local_elements = dict()
        self.walk_elements(soup, '/')
        self.add_to_model(self.local_elements)
        self.local_elements = None
  
    def visit_leaf_element(self, node, path):
        node_string = self.clean_string(node.string)
        if node_string:
            path_signature = self.signature(path)
            text_signature = self.signature('', node_string)
            #print >>sys.stderr, path_signature, text_signature.encode("utf-8")
            if path_signature in self.local_elements:
                self.local_elements[path_signature][text_signature] = 1
            else:
                self.local_elements[path_signature] = {text_signature: 1}
        
    def walk_elements(self, soup, path = '/'):
        content = ''
        count = 0
        for node in soup.contents:
            count += 1

            if isinstance(node, NavigableString):
                self.visit_leaf_element(node, path + "@" + str(count))
            elif isinstance(node, Tag):
                attrs = ''
                if node.get('class'):
                    attrs += '.' + node['class']
                if node.get('id'):
                    # Remove all hex. strings from id
                    node_id = re.sub(r'(?i)[\da-z]*\d[\da-z]*', '1', node['id'])
                    attrs += '#' + node_id
  
                sub_path = path + node.name + attrs + '/'
                self.walk_elements(node, sub_path)


        

class PageCleaner(CleanupModelLearner):
    """Clean web pages based on a previously learned model"""

    def __init__(self, cleanup_model=None, cleanup_threshold=0.1, **kwargs):
        """Initialize cleanup model learner.
        
        Takes standard parameters of Extractor, plus:
         - cleanup_model: filename of the model to load, or model itself
         - cleanup_threshold: 0 means less conservative, 1 means more conservative
        """
       
        Extractor.__init__(self, **kwargs)
        self.cleanup_model = cleanup_model
        self.cleanup_threshold = cleanup_threshold
        
        assert self.cleanup_model, "PageCleaner extractor requires a cleanup model"
       
        self.load_model(self.cleanup_model)

    def remove_empty_elements(self, root):
        nodes = copy.copy(root.contents)
        for node in nodes:
            if isinstance(node, NavigableString):
                # Remove empty (or rather, whitespace-only) strings
                if not self.clean_string(node.string):
                    node.extract()
            elif isinstance(node, Tag):
                # Clean the node recursively
                self.remove_empty_elements(node)
                # Keep <br/> and <hr/> elements
                if node.name not in ('br', 'hr'):
                    # Remove nodes without any content 
                    has_child_with_content = False
                    for child  in node.contents:
                         if isinstance(child, NavigableString) \
                            or (isinstance(child, Tag) and child.name not in ('br', 'hr')):
                            has_child_with_content = True
                            break
                    if not has_child_with_content:
                        node.extract()

    def extract_from_soup(self, soup, filename, relative_filename):
        self.nodes_to_remove = []
        
        self.walk_elements(soup, '/')
        
        for node in self.nodes_to_remove:
            node.extract()
            
        self.remove_empty_elements(soup)
                
        return soup  
        
    def visit_leaf_element(self, node, path):
        node_string = self.clean_string(node.string)
        if node_string:
            signature = self.signature(path)
            if signature in self.skip_paths and self.skip_paths[signature] > self.cleanup_threshold:
                self.nodes_to_remove.append(node)

        

