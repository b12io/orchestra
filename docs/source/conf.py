# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

from django.conf import settings
settings.configure()

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',

    # Autoformat docstrings based on Google style.
    'sphinx.ext.napoleon',

    # Autoformat API endpoints.
    'sphinxcontrib.httpdomain',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = u'Orchestra'
copyright = u'2015, Unlimited Labs'
author = u'B12'

version = '0.1'
release = '0.1.2'

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
