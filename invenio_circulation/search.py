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

"""Configuration for circulation search."""
from elasticsearch_dsl.query import Bool, MultiMatch, Range

from invenio_search import RecordsSearch

from .api import Item


class ItemSearch(RecordsSearch):
    """Default search class."""

    class Meta:
        """Configuration for circulation search."""

        index = 'circulation-item'
        doc_types = None


class ItemRevisionSearch(object):
    """Search class utilizing `Item.find_by_holding`.

    Since this function doesn't utilize elasticsearch, ItemRevisionSearch
    has to mimick certain aspects of `elasticsearch_dsl.Search`.
    """

    class Meta:
        """Configuration for circulation search."""

        index = 'circulation-item'
        doc_types = None

    class Results(object):
        """Substitution of `elasticsearch_dsl.result.Result."""

        class Hits(object):
            """Wrapper class for the search hits."""

        def __init__(self, results):
            """Constructor to wrap the search results."""
            self.hits = self.Hits()
            self.hits.total = len(results)
            self.results = results

        def to_dict(self):
            """Convert results into a dictionary."""
            return {
                'hits': {
                    'hits': self.results,
                    'total': self.hits.total
                }
            }

    def __init__(self):
        """Constructor for `elasticsearch_dsl.result.Result substituion.

        Adds dummy `_index` value.
        """
        self._index = ['']
        self._query = {}

    def query(self, q, *args, **kwargs):
        """Set the desired query."""
        if type(q) is not Bool:
            q = Bool(must=[q])
        for must in q.must:
            if type(must) == MultiMatch:
                for field in must.fields:
                    self._query[field] = must.query
            elif type(must) == Range:
                for key, value in must._params.items():
                    self._query[key] = [value['gte'], value['lte']]
        return self

    def __getitem__(self, *args, **kwargs):
        """Support slicing of the search results. Currently not implemented."""
        return self

    def params(self, *args, **kwargs):
        """Specify query params to be used. Currently not implemented."""
        return self

    def execute(self):
        """Execute the search.

        :returns: ItemRevisionSearch.Results
        """
        res = []
        for uuid, revision in Item.find_by_holding(**self._query):
            item = Item.get_record(uuid)
            res.append(item.revisions[revision-2])

        return self.Results(res)
