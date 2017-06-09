import os
import sys
import warnings

import ConfigParser

'''
Usage:
from pyclarity_lims.config import BASEURI, USERNAME, PASSWORD

Alternate Usage: 
from pyclarity_lims import config
BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = config.load_config(specified_config = <path to config file>) 
'''

spec_config = None

def get_config_info(config_file):
    config = ConfigParser.SafeConfigParser()
    config.readfp(open(config_file))
    
    
    BASEURI = config.get('pyclarity_lims', 'BASEURI').rstrip()
    USERNAME = config.get('pyclarity_lims', 'USERNAME').rstrip()
    PASSWORD = config.get('pyclarity_lims', 'PASSWORD').rstrip()
    
    if config.has_section('pyclarity_lims') and config.has_option('pyclarity_lims','VERSION'):
        VERSION = config.get('pyclarity_lims', 'VERSION').rstrip()
    else:
        VERSION = 'v2'
        
    if config.has_section('logging') and config.has_option('logging','MAIN_LOG'):
        MAIN_LOG = config.get('logging', 'MAIN_LOG').rstrip()
    else:
        MAIN_LOG = None
    return BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG
        

def load_config(specified_config = None):
    if specified_config != None:
        config_file = specified_config
    else:
        config = ConfigParser.SafeConfigParser()
        try:
            conf_file = config.read([os.path.expanduser('~/.genologicsrc'), '.genologicsrc',
                        'pyclarity_lims.conf', 'pyclarity_lims.cfg', '/etc/pyclarity_lims.conf'])

            # First config file found wins
            config_file = conf_file[0]

        except:
            warnings.warn("Please make sure you've created or indicated your own Genologics configuration file (i.e: ~/.genologicsrc) as stated in README.md")
            sys.exit(-1)

    BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = get_config_info(config_file)

    return BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG   
    

BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = load_config(specified_config = spec_config)
