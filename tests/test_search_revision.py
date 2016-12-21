# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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


"""Revision search tests."""

import datetime
import json

import pytest
from elasticsearch_dsl.query import Bool, MultiMatch, Range

from invenio_circulation.api import Item, ItemStatus, Location
from invenio_circulation.search import ItemRevisionSearch
from invenio_circulation.validators import LoanItemSchema


def test_item_revision_search_result():
    search_result = ['result1', 'result2']
    result = ItemRevisionSearch.Results(search_result)

    assert result.hits.total == len(search_result)
    assert result.results == search_result
    assert result.to_dict() == {
        'hits': {
            'hits': search_result,
            'total': len(search_result)
        }
    }


def test_item_revision_search_query():
    # Testing the initial setup
    item_revision_search = ItemRevisionSearch()

    assert item_revision_search._index == ['']
    assert item_revision_search._query == {}

    # Testing a MultiMatch query
    item_revision_search = ItemRevisionSearch()
    mm = MultiMatch(fields=['foo'], query='bar')

    item_revision_search.query(mm)

    assert item_revision_search._query == {'foo': 'bar'}

    # Testing a range query
    item_revision_search = ItemRevisionSearch()
    r = Range(foo={'gte': 'bar', 'lte': u'baz'})

    item_revision_search.query(r)

    assert item_revision_search._query == {'foo': ['bar', 'baz']}


def test_item_revision_search_execute(app, db):
    # Prepare the item
    item = Item.create({'foo': 'bar'})
    db.session.commit()

    # Create loan data
    la = LoanItemSchema()
    la.context['item'] = item

    # Prepare the loan data
    tmp = la.load({'user_id': 1}).data
    data = la.dump(tmp).data

    # Loan item
    item.loan_item(**data)
    item.commit()
    db.session.commit()

    # Return item
    item.return_item()
    item.commit()
    db.session.commit()

    # Prepare ItemRevisionSearch
    item_revision_search = ItemRevisionSearch()
    mm = MultiMatch(fields=['user_id'], query=1)

    result = item_revision_search.query(mm).execute()

    assert result.hits.total == 1
    assert result.to_dict() == {
        'hits': {
            'hits': [item],
            'total': 1
        }
    }


def test_item_revision_search_dummies():
    """Tests necessary dummy implementations."""
    item_revision_search = ItemRevisionSearch()

    assert item_revision_search == item_revision_search[0]
    assert item_revision_search == item_revision_search.params()
