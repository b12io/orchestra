# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

# Methods in task_lifecycle currently require the ORCHESTRA_PATHS
# setting; this will change when workflows are moved into the database.
from django.conf import settings
settings.configure(ORCHESTRA_PATHS=())

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',

    # Autoformat docstrings based on Google style.
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = u'Orchestra'
copyright = u'2015, Unlimited Labs'
author = u'Unlimited Labs'

version = '0.1'
release = '0.1.0'

exclude_patterns = ['_build']

pygments_style = 'sphinx'

todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

html_static_path = ['_static']

htmlhelp_basename = 'Orchestradoc'

# -- Options for manual page output ---------------------------------------

man_pages = [
    (master_doc, 'orchestra', u'Orchestra Documentation',
     [author], 1)
]

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = [
    (master_doc, 'Orchestra', u'Orchestra Documentation',
     author, 'Orchestra', ('An open source system to orchestrate teams of '
                           'experts as they complete complex projects with '
                           'the help of automation.'),
     'Miscellaneous'),
]
