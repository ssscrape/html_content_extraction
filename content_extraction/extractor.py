"""Generic content extractor"""


import os, sys, traceback
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, PageElement, Tag, NavigableString, Comment, Declaration, ProcessingInstruction
from datetime import datetime, date
import xml.dom.minidom
import subprocess
import re

import chardet

BLOCK_LEVEL_TAGS = set(['address', 'blockquote', 'center', 'dir', 'div', 'dl', 
                        'fieldset', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                        'hr', 'isindex', 'menu', 'noframes', 'noscript', 'ol', 
                        'p', 'pre', 'table', 'ul', 'dd', 'dt', 'frameset', 
                        'li', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr',
                        'br']) 
 

class Extractor:
    """Generic content extractor"""

    def __init__(self, output_dir=None, output_format="xml", overwrite=False, flatten_files=False, encoding=None, **kwargs):
        """Initialize an extractor with given options.
        
        Available options:
         - output_dir: where to store the results
         - output_format: 'xml', 'html', 'txt' or 'soup'
         - overwrite: whether to overwrite existing files
         - flatten_files: whether to flatten directory/filename structure when saving files
        """

        self.output_dir = output_dir
        self.output_format = output_format
        self.overwrite = overwrite
        self.flatten_files = flatten_files
        self.encoding = encoding

        self.last_file_id = 0
        
        if self.output_dir and not os.path.isdir(self.output_dir):
           os.mkdir(self.output_dir)

    def finish(self):
        """Finish the extraction; can be redefined in ancestors to perform something meaningful.

        Returns None, or anything that can
        """
        
        return None

    def extract(self, files=None, htmls=None, soups=None, output=None):
        """Extract information from files or directories.
        
        Parameters:
         - files: list of names of files or directories where to search for data
         - htmls: list of strings: the content of individual HTML documents
         - soups: list of instances of BeautifulSoup (parsed HTML pages)
         - output: file descriptor where to write output, or None

        If 'output' is defined, returns None. Otherwise returns a list of extraction results 
        for all files/docs/soups. The order in the result list is the same as the order in
        the input docs/soups.
        """
        
        results = []

        if output and self.output_format == 'xml':
                print >>output, "<data>" 

        if htmls: 
            for html in htmls:
                result = self.extract_from_html(html=html)
                self._process_result(result, output, results)
        
        if soups: 
            for soup in soups:
                self.cleanup_soup(soup)
                result = self.extract_from_soup(soup, "", "")
                self._process_result(result, output, results)
       
        if files: 
            for dir_or_file in files:
                dir_or_file = os.path.abspath(dir_or_file) 
                
                if os.path.isdir(dir_or_file):
                    # input is a directory
                    dir_name = dir_or_file
                    for path, dirs, files in os.walk(dir_name):
                        for file in files:
                            filename = os.path.join(path, file)
                            relative_filename = re.sub('^' + dir_name + '/*', '', filename)
                            result = self.extract_from_file(filename, relative_filename)
                            if result is not None:
                                self._process_result(result, output, results)
                else:
                    # input is a file
                    filename = dir_or_file
                    assert os.path.exists(filename), filename + " does not exist"
                    relative_filename = os.path.basename(filename)
                    result = self.extract_from_file(filename, relative_filename)
                    if result is not None:
                        self._process_result(result, output, results)

        result = self.finish()
        self._process_result(result, output, results)

        if output and self.output_format == 'xml':
                print >>output, "</data>" 

        return results


    def _process_result(self, result, output, results):    
        if output:
            if isinstance(result, unicode):
                result = result.encode("utf-8")
            print >>output, result
        else:    
            results.append(result)


    def extract_from_file(self, filename, relative_filename=None):
        """Extract information from a file; return the result of extraction, or None if it cannot be computer or is saved to a file"""
        
        if not relative_filename:
            relative_filename = filename
            
        output_filename = None    
        if self.output_dir:
            if self.flatten_files:
                self.last_file_id += 1
                relative_filename = str(self.last_file_id) + "." + self.output_format
            output_filename = os.path.join(self.output_dir, relative_filename) 

        if output_filename and os.path.exists(output_filename) and not self.overwrite:
            print >>sys.stderr, "Skipping", filename, ": existing", output_filename
            return None
        

        print >>sys.stderr, "Processing", filename 
            
        res = None
        if self.is_html_file(filename):
            res = self.extract_from_html(filename=filename, relative_filename=relative_filename)
       
        if not output_filename:
            return res

        output_dir_name = os.path.dirname(output_filename)
        if output_dir_name and not os.path.isdir(output_dir_name):
            os.makedirs(output_dir_name)
        print >>sys.stderr, '    ', "saving output to", output_filename    
        f = open(output_filename, 'w')
        print >>f, res
        f.close()

        return None

    def cleanup_soup(self, soup):
        """Remove scripts, styles, iframes, comments from soup"""
        for node in soup.findAll(['script', 'style', 'iframe']) + \
                    soup.findAll(text=lambda text:isinstance(text, (Comment, Declaration, ProcessingInstruction))):
            node.extract()

            
            
    def extract_from_html(self, html=None, filename=None, relative_filename=None):
        """Extract information from an HTML file.
        
        Parameters:
          - html: string containing HTML of the document
          - filename: file name of the document (either html or filename should be given)
          - relative_filename: file name relative to the root directory
        """

        if filename:
            f = open(filename)
            html = f.read()
            f.close()
        
        assert(html is not None)

        # Try to guess encoding
        encoding = self.encoding
        if encoding is None:
            res = chardet.detect(html)
            if 'encoding' in res:
                encoding = res['encoding']

        print >>sys.stderr, "Encoding: ", encoding    

        # Hack to handle <BR> and <HR> tags: convert them to paragraphs <P>
        #html = re.sub('(?i)<(br|hr)\W*>', '<p>', html)    
        
        # Hack: remove non-standard <wbr> tag that BeautifulSoup chokes on
        html = re.sub('(?i)<wbr\s*\/?\s*>', '', html)    
        
        soup = None
        try:
            soup = BeautifulSoup(html, fromEncoding=encoding, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        except StandardError, e:
            print >>sys.stderr, "ERROR parsing HTML from", filename 
            traceback.print_exc()
            return
                
        res = None
        try:
            self.cleanup_soup(soup)
            res = self.extract_from_soup(soup, filename=filename, relative_filename=relative_filename)
        except StandardError, e:
            print >>sys.stderr, "ERROR extracting from", filename 
            traceback.print_exc()
            return
                        
        if res:                    
            try:
                if isinstance(res, Tag):
                    # Extraction result is a tag from BeautifulSoup
                    if filename:
                        res['filename'] = filename
                    if self.output_format == 'soup':
                        return res
                    elif self.output_format == 'txt':
                        return self.soup_to_text(res)
                    else:    
                        return res.prettify()
                else:
                    # Extraction result is an object: serialize as XML, ignoring output_format
                    res = self.serialize_to_xml(res)
                    if filename:
                        res.setAttribute('filename', filename)
                    return res.toprettyxml('    ', '\n', 'utf8')
            except StandardError, e:
                print >>sys.stderr, "ERROR generating output for", filename 
                traceback.print_exc()
                return None
                
    @staticmethod
    def soup_to_text(soup):

        # Remove scripts, styles, iframes, comments
        for node in soup.findAll(['script', 'style', 'iframe']) + \
                    soup.findAll(text=lambda text:isinstance(text, (Comment, Declaration, ProcessingInstruction))):
            node.extract()

        # Keep only page title and body, extract only raw text
        text = ''
        newline = True
        for node in soup.findAll(['body']):
            for e in node.recursiveChildGenerator():
                if isinstance(e,unicode):
                    text += re.sub(r"\s+", " ", e)
                elif isinstance(e, Tag) and e.name.lower() in BLOCK_LEVEL_TAGS:
                    text += "\n"

        # Avoid three or more empty lines in a row
        text = re.sub(r"\n\s*\n\s*\n", "\n", text)
           
        return text    
   
    def extract_from_soup(self, soup, filename, relative_filename):
        """Extract data from a parsed HTML (BeautifulSoup) obtained from a given file."""

        raise NotImplementedError("plugins must define extract_from_soup()")


    def is_html_file(self, filename):
        ret = subprocess.call('file "%s" | grep -q HTML' % filename, shell=True)
        if ret == 0:
            return True
        else:
            return False
     


    def get_text(self, node):
        text = ''
        for e in node.recursiveChildGenerator():
            if isinstance(e, Comment) or isinstance(e, Declaration) or isinstance(e, ProcessingInstruction):
                pass
            elif isinstance(e,unicode):
                text += e
            elif isinstance(e, Tag) and e.name.lower() in ('p', 'br'):
                text += '-NEWLINE-'
        text = self.clean_string(text)        
        return text                  


    def clean_string(self, s):
        s = re.sub('(?i)&\w*quo\w*;', '"', s)
        s = re.sub('(?i)&#*\w+;', ' ', s)
        s = re.sub('\s+', ' ', s)
        s = re.sub(r'\s*(-NEWLINE-\s*)+', '\n', s)
        s = re.sub('^\s+|\s+$', '', s)
        return s


    def serialize_to_xml(self, obj, tag_name = 'items', parent = None, doc = None):
        """Convert object to XML"""    
        
        return_doc = False
        if not doc:
            doc = xml.dom.minidom.Document()
            return_doc = True

        if not parent:
            parent = doc.createElement(tag_name)
            doc.appendChild(parent)      
          
        if isinstance(obj, (int, datetime, date)):
            res = doc.createElement(tag_name)
            res.appendChild(doc.createTextNode(unicode(obj)))
            parent.appendChild(res)
        elif isinstance(obj, basestring):
            res = doc.createElement(tag_name)
            res.appendChild(doc.createTextNode(self.clean_string(obj)))
            parent.appendChild(res)
        elif isinstance(obj, list):
            for elt in obj:
                self.serialize_to_xml(elt, tag_name, parent, doc)
        elif hasattr(obj, '__class__'):
            tag_name = re.sub('.*\.', '', str(obj.__class__).lower())
            res = doc.createElement(tag_name)
            for elt in sorted(obj.__dict__):
                self.serialize_to_xml(getattr(obj, elt), elt, res, doc)
            parent.appendChild(res)            
        else:
            raise NotImplementedError("don't know how to serialize %s %s", type(obj), obj)          
        
        if return_doc:            
            return parent



def nicer_writexml(self, writer, indent="", addindent="", newl=""):
        """Hack to make the output of xml.dom.minidom.toprettyxml nicer"""
        # indent = current indentation
        # addindent = indentation to add to higher levels
        # newl = newline string
        writer.write(indent+"<" + self.tagName)

        attrs = self._get_attributes()
        a_names = attrs.keys()
        a_names.sort()

        for a_name in a_names:
            writer.write(" %s=\"" % a_name)
            xml.dom.minidom._write_data(writer, attrs[a_name].value)
            writer.write("\"")
        if self.childNodes:
            if len(self.childNodes) == 1 and self.childNodes[0].nodeType == xml.dom.minidom.Node.TEXT_NODE:
                writer.write(">")
                self.childNodes[0].writexml(writer, "", "", "")
                writer.write("</%s>%s" % (self.tagName, newl))
                return
            writer.write(">%s"%(newl))
            for node in self.childNodes:
                node.writexml(writer,indent+addindent,addindent,newl)
            writer.write("%s</%s>%s" % (indent,self.tagName,newl))
        else:
            writer.write("/>%s"%(newl))


# Replace writexml() with the hacked version
xml.dom.minidom.Element.writexml = nicer_writexml


