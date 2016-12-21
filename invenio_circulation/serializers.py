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

"""Serializers for circulation search."""
import json

from invenio_records_rest.serializers import JSONSerializer
from invenio_records_rest.serializers.response import search_responsify
from invenio_records_rest.serializers.schemas.json import RecordSchemaJSONV1


class RevisionSerializer(JSONSerializer):
    """JSON serializer for items found by `Item.find_by_holding`."""

    def serialize_search(self, pid_fetcher, search_result, links=None,
                         item_links_factory=None):
        """Serialize a search result.

        :param search_result: Elasticsearch search result.
        :param links: Dictionary of links to add to response.
        """
        return json.dumps({
            'hits': {
                'hits': [hit for hit in search_result['hits']['hits']],
                'total': search_result['hits']['total'],
            },
            'links': links or {},
            'aggregations': search_result.get('aggregations', {}),
        }, **self._format_args())


revision_serializer = search_responsify(RevisionSerializer(RecordSchemaJSONV1),
                                        'application/json')
