# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from unittest.mock import MagicMock
sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'INDRA Network Search'
copyright = '2021, K. Karis'
author = 'K. Karis'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinxcontrib.autodoc_pydantic',
]

# The master toctree document.
master_doc = 'index'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

mock_modules = ['depmap_analysis', 'depmap_analysis.network_functions',
                'depmap_analysis.network_functions.famplex_functions',
                'depmap_analysis.network_functions.net_functions',
                'depmap_analysis.util', 'depmap_analysis.util.io_functions',
                'depmap_analysis.util.aws',
                'depmap_analysis.scripts',
                'depmap_analysis.scripts.dump_new_graphs',
                'indra_db', 'indra_db.util', 'indra_db.client',
                'indra_db.util.s3_path',
                'indra_db.client.readonly', 'indra_db.client.principal',
                'indra_db.client.principal.curation',
                'indra_db.client.readonly.query',
                'indra_db.client.readonly.mesh_ref_counts',
                'indra_db.util.dump_sif']

for mod in mock_modules:
    sys.modules[mod] = MagicMock()
