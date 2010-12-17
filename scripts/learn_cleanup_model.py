"""Generate model for cleaning up pages of a crawled website
"""

import os, sys
from optparse import OptionParser


from content_extraction.cleanup import CleanupModelLearner


if __name__ == "__main__":
    parser = OptionParser("usage: %prog [options] input_files_or_dirs...",
                          description=__doc__)

    parser.add_option("-O", "--output_format", dest="output_format", 
                      help="output format: pickle or python (default: python)", 
                      default='python')
    parser.add_option("-d", "--max_duplicates", dest="max_duplicates", 
                      help="""Maximum number of duplicate files in the input dataset
                              (default: 2)""", 
                      metavar="NUM",   
                      default=2)

                      
                      
    (options, params) = parser.parse_args()
    options.output_dir = None
        
    if len(params) < 1:
        parser.print_help()
        exit(1)
        
    input_files = params

    learner = CleanupModelLearner(**options.__dict__)
 
    # Call learner for all input files/dirs
    learner.extract(files=input_files)
        
    print learner.get_model(format=options.output_format)    
