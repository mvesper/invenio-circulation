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

"""Invenio module for the circulation of bibliographic items.

Using the module
================

Following below a few quick examples of how to use the module.

Creating items
--------------
    >>> # doctest setup
    >>> import doctest
    >>> doctest.ELLIPSIS_MARKER = '-etc-'
    >>>
    >>> from invenio_db import db
    >>> from invenio_indexer.api import RecordIndexer
    >>>
    >>> from invenio_circulation.api import Item
    >>> from invenio_circulation.minters import circulation_item_minter
    >>>
    >>>
    >>> item = Item.create({
    ...     'foo': 'bar',
    ...     'title_statement': {'title': 'title'},
    ...     'record': {'id': 1}
    ... }) #doctest: +ELLIPSIS
    -etc-
    >>> pid = circulation_item_minter(item.id, item) #doctest: +ELLIPSIS
    -etc-
    >>> item.commit() #doctest: +ELLIPSIS
    -etc-
    >>> db.session.commit() #doctest: +ELLIPSIS
    -etc-
    >>>
    >>> record_indexer = RecordIndexer()
    >>> record_indexer.index(item) #doctest: +ELLIPSIS
    -etc-


Resolving items
---------------
    >>> from invenio_circulation.api import Item
    >>> from invenio_pidstore.resolver import Resolver
    >>>
    >>> pid_value = 1 # whatever pid value is at hand
    >>>
    >>> resolver = Resolver(pid_type='crcitm', object_type='rec',
    ...                     getter=Item.get_record)
    >>> _, record = resolver.resolve(pid_value) #doctest: +ELLIPSIS
    -etc-


Getting the pid values
----------------------
    >>> from invenio_circulation.models import CirculationItemIdentifier
    >>>
    >>> ids = sorted(
    ...     [x.recid for x in CirculationItemIdentifier.query.all()]
    ... ) #doctest: +ELLIPSIS
    -etc-


Searching for items
-------------------
    >>> from invenio_circulation.search import ItemSearch
    >>> from elasticsearch_dsl import Q
    >>>
    >>> results = ItemSearch().query(Q('match', foo='bar0')).execute()


Creating/validating the payloads
--------------------------------
    >>> from invenio_circulation.api import Item
    >>> from invenio_circulation.validators import *
    >>>
    >>> item = Item({'_circulation': {'status': 'on_shelf', 'holdings': []}})
    >>>
    >>> # validators ending in `ItemSchema` correspond to `api.Item` methods
    >>> loan_item_schema = LoanItemSchema()
    >>> loan_item_schema.context['item'] = item
    >>>
    >>> data, errors = loan_item_schema.load({})
    >>> payload, _errors = loan_item_schema.dump(data)
    >>>
    >>> item.loan_item(**payload)

The following payloads are required for the corresponding actions:

`loan_item` - LoanItemSchema
 {'delivery': <mail or delivery>,
  'end_date': <date>,
  'start_date': <date>,
  'user_id': <id>,
  'waitlist': <Boolean}

`request_item` - RequestItemSchema
 {'delivery': <mail or delivery>,
  'end_date': <date>,
  'start_date': <date>,
  'user_id': <id>,
  'waitlist': <Boolean}

`return_item` - ReturnItemSchema
 {}

`lose_item` - <no item schema>
 {}

`return_missing_item` - ReturnMissingItemSchema
 {}

`cancel_hold` - CacelItemSchema
 {'hold_id': <uuid.uuid4>}

`extend_loan` - ExtendItemSchema
 {'requested_end_date': <date>}


Creating test data
==================

Set the environment variable `FLASK_APP` to the location of examples/app.py.
Then call `flask fixtures items` to create example items and
`flask fixtures user` to create example users for the circulation module.
"""

from __future__ import absolute_import, print_function

from .ext import InvenioCirculation, InvenioCirculationREST
from .version import __version__

__all__ = ('__version__', 'InvenioCirculation', 'InvenioCirculationREST')
