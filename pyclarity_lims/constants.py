"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

import re
from xml.etree import ElementTree

_NSMAP = dict(
        art='http://pyclarity_lims.com/ri/artifact',
        artgr='http://pyclarity_lims.com/ri/artifactgroup',
        cnf='http://pyclarity_lims.com/ri/configuration',
        con='http://pyclarity_lims.com/ri/container',
        ctp='http://pyclarity_lims.com/ri/containertype',
        exc='http://pyclarity_lims.com/ri/exception',
        file='http://pyclarity_lims.com/ri/file',
        inst='http://pyclarity_lims.com/ri/instrument',
        lab='http://pyclarity_lims.com/ri/lab',
        prc='http://pyclarity_lims.com/ri/process',
        prj='http://pyclarity_lims.com/ri/project',
        prop='http://pyclarity_lims.com/ri/property',
        protcnf='http://pyclarity_lims.com/ri/protocolconfiguration',
        protstepcnf='http://pyclarity_lims.com/ri/stepconfiguration',
        prx='http://pyclarity_lims.com/ri/processexecution',
        ptm='http://pyclarity_lims.com/ri/processtemplate',
        ptp='http://pyclarity_lims.com/ri/processtype',
        res='http://pyclarity_lims.com/ri/researcher',
        ri='http://pyclarity_lims.com/ri',
        rt='http://pyclarity_lims.com/ri/routing',
        rtp='http://pyclarity_lims.com/ri/reagenttype',
        kit='http://pyclarity_lims.com/ri/reagentkit',
        lot='http://pyclarity_lims.com/ri/reagentlot',
        smp='http://pyclarity_lims.com/ri/sample',
        stg='http://pyclarity_lims.com/ri/stage',
        stp='http://pyclarity_lims.com/ri/step',
        udf='http://pyclarity_lims.com/ri/userdefined',
        ver='http://pyclarity_lims.com/ri/version',
        wkfcnf='http://pyclarity_lims.com/ri/workflowconfiguration'
)

for prefix, uri in _NSMAP.items():
    ElementTree._namespace_map[uri] = prefix

_NSPATTERN = re.compile(r'(\{)(.+?)(\})')


def nsmap(tag):
    "Convert from normal XML-ish namespace tag to ElementTree variant."
    parts = tag.split(':')
    if len(parts) != 2:
        raise ValueError("no namespace specifier in tag")
    return "{%s}%s" % (_NSMAP[parts[0]], parts[1])
