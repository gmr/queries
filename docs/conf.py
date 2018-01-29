# -*- coding: utf-8 -*-
import datetime
import sys

sys.path.insert(0, '../')

import queries

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'Queries'
copyright = '2014 - {}, Gavin M. Roy'.format(
    datetime.date.today().strftime('%Y'))
release = queries.__version__
version = '.'.join(release.split('.')[0:1])
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'Queriesdoc'
latex_elements = {}
latex_documents = [
  ('index', 'Queries.tex', u'Queries Documentation',
   u'Gavin M. Roy', 'manual'),
]
man_pages = [
    ('index', 'queries', u'Queries Documentation',
     [u'Gavin M. Roy'], 1)
]
texinfo_documents = [
  ('index', 'Queries', u'Queries Documentation',
   u'Gavin M. Roy', 'Queries', 'PostgreSQL Simplified',
   'Miscellaneous'),
]
intersphinx_mapping = {'psycopg2': ('http://initd.org/psycopg/docs/', None),
                       'tornado': ('http://www.tornadoweb.org/en/stable', None)}
