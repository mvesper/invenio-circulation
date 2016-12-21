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


"""Revision serializer tests."""

import json
import pytest

from invenio_circulation.serializers import RevisionSerializer


def test_serialize_search():

    val1 = {'_source': {'title': 'test1', 'pid': '1'}, '_id': 'a',
            '_version': 1}
    val2 = {'_source': {'title': 'test2', 'pid': '2'}, '_id': 'b',
            '_version': 1}

    data = json.loads(RevisionSerializer(None).serialize_search(
        None,
        {
            'hits': {
                'hits': [val1, val2],
                'total': 2,
            },
            'aggregations': {},
        }
    ))

    assert data['aggregations'] == {}
    assert 'links' in data
    assert data['hits'] == {
        'hits': [val1, val2],
        'total': 2,
    }
