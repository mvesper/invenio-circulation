# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Invenio module for the circulation of bibliographic items."""

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'isort>=4.2.5',
    'pep257>=0.7.0',
    'psycopg2>=2.6.1',
    'pydocstyle>=1.0.0',
    'pytest-cache>=1.0',
    'pytest-cov>=1.8.0',
    'pytest-pep8>=1.0.6',
    'pytest>=2.8.0',
]

extras_require = {
    'docs': [
        'Sphinx>=1.4.2',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup_requires = [
    'Babel>=1.3',
]

install_requires = [
    'Flask-BabelEx>=0.9.3',
    'invenio-accounts>=1.0.0a10',
    'invenio-db>=1.0.0a9',
    'invenio-indexer>=1.0.0a3',
    'invenio-jsonschemas>=1.0.0a3',
    'invenio-mail>=1.0.0a3',
    'invenio-pidstore>=1.0.0a7',
    'invenio-records-rest>=1.0.0a15',
    'invenio-records>=1.0.0a15',
    'invenio-search>=1.0.0a7',
    'invenio-userprofiles>=1.0.0a5'
]

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('invenio_circulation', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

fetcher_str = '{0} = invenio_circulation.fetchers:{1}'
item_fetcher = fetcher_str.format('circulation_item',
                                  'circulation_item_fetcher')
loan_cycle_fetcher = fetcher_str.format('circulation_loan_cycle',
                                        'circulation_loan_cycle_fetcher')
location_fetcher = fetcher_str.format('circulation_location',
                                      'circulation_location_fetcher')

minter_str = '{0} = invenio_circulation.minters:{1}'
item_minter = minter_str.format('circulation_item',
                                'circulation_item_minter')
loan_cycle_minter = minter_str.format('circulation_loan_cycle',
                                      'circulation_loan_cycle_minter')
location_minter = minter_str.format('circulation_location',
                                    'circulation_location_minter')

setup(
    name='invenio-circulation',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio circulation holdings library ILS',
    license='GPLv2',
    author='CERN',
    author_email='info@invenio-software.org',
    url='https://github.com/inveniosoftware/invenio-circulation',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'invenio_base.apps': [
            'invenio_circulation = invenio_circulation:InvenioCirculation',
        ],
        'invenio_i18n.translations': [
            'messages = invenio_circulation',
        ],
        'invenio_db.models': [
            'invenio_circulation = invenio_circulation.models',
        ],
        'invenio_search.mappings': [
            'circulation = invenio_circulation.mappings',
        ],
        'invenio_jsonschemas.schemas': [
            'circulation = invenio_circulation.schemas',
        ],
        'invenio_pidstore.fetchers': [
            item_fetcher,
            loan_cycle_fetcher,
            location_fetcher
        ],
        'invenio_pidstore.minters': [
            item_minter,
            loan_cycle_minter,
            location_minter
        ]
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 1 - Planning',
    ],
)
