from __future__ import absolute_import

try:
    from galaxy import eggs
    eggs.require("PyYAML")
except ImportError:
    pass

import yaml

from .yaml import YamlToolSource
from .xml import XmlToolSource

from galaxy.tools.loader import load_tool as load_tool_xml


import logging
log = logging.getLogger(__name__)


def get_tool_source(config_file):
    if config_file.endswith(".yml"):
        log.info("Loading tool from YAML - this is experimental - tool will not function in future.")
        with open(config_file, "r") as f:
            as_dict = yaml.load(f)
            return YamlToolSource(as_dict)
    else:
        tree = load_tool_xml(config_file)
        root = tree.getroot()
        return XmlToolSource(root)
