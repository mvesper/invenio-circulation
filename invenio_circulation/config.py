# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Invenio circulation configuration file."""

import datetime


CIRCULATION_EMAIL_SENDER = None
CIRCULATION_LOAN_PERIOD = 28

CIRCULATION_LOCATION_SCHEMA = 'circulation/location-v1.0.0.json'
CIRCULATION_ITEM_SCHEMA = 'circulation/item/default-v1.0.0.json'

CIRCULATION_DATE_FORMAT = '%Y-%m-%d'
"""Datetime format used to parse date strings."""

CIRCULATION_REST_ENDPOINTS = {
    'crcitm': {
        'default_endpoint_prefix': True,
        'pid_type': 'crcitm',
        'pid_minter': 'circulation_item',
        'pid_fetcher': 'circulation_item',
        'record_class': 'invenio_circulation.api:Item',
        'record_serializers': {
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        'search_class': 'invenio_circulation.search:ItemSearch',
        'search_index': None,
        'search_type': None,
        'search_serializers': {
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        'list_route': '/circulation/items/',
        'item_route': '/circulation/items/<pid(crcitm):pid_value>',
        'default_media_type': 'application/json',
        'max_result_window': 10000,
    },
    'crcitmrev': {
        'pid_type': 'crcitm',
        'pid_minter': 'circulation_item',
        'pid_fetcher': 'circulation_item',
        'record_class': 'invenio_circulation.api:Item',
        'record_serializers': {
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        'search_class': 'invenio_circulation.search:ItemRevisionSearch',
        'search_index': None,
        'search_type': None,
        'search_serializers': {
            'application/json': ('invenio_circulation.serializers'
                                 ':revision_serializer'),
        },
        'list_route': '/circulation/item_revisions/',
        'item_route': '/circulation/item_revisions/<pid(crcitm):pid_value>',
        'default_media_type': 'application/json',
        'max_result_window': 10000,
    }
}
"""Basic REST circulation configuration."""

CIRCULATION_ITEM_SEARCH_API = '/api/circulation/items/'
"""Configure the item search engine endpoint."""

CIRCULATION_USER_SEARCH_API = '/api/users/'
"""Configure the user search engine endpoint."""

CIRCULATION_ACTION_LOAN_URL = '/api/hooks/receivers/circulation_loan/events/'
CIRCULATION_ACTION_REQUEST_URL = \
    '/api/hooks/receivers/circulation_request/events/'
CIRCULATION_ACTION_RETURN_URL = \
    '/api/hooks/receivers/circulation_return/events/'
CIRCULATION_ACTION_EXTEND_URL = \
    '/api/hooks/receivers/circulation_extend/events/'
CIRCULATION_ACTION_LOSE_URL = '/api/hooks/receivers/circulation_lose/events/'
CIRCULATION_ACTION_CANCEL_URL = \
    '/api/hooks/receivers/circulation_cancel/events/'

CIRCULATION_USER_HUB_QUERY = '_circulation.holdings.user_id:'


def latest_loans_query():
    today = datetime.date.today().isoformat()
    return ('_circulation.status:on_loan AND '
            '_circulation.holdings.start_date:1970-01-01->{0} AND '
            '_circulation.holdings.end_date:{0}->9999-01-01').format(today)


def overdue_loans_query():
    yesterday = (datetime.date.today() -
                 datetime.timedelta(days=1)).isoformat()
    return ('_circulation.status:on_loan AND '
            '_circulation.holdings.end_date:1970-01-01->{0}').format(yesterday)


def items_on_shelf_with_holds_query():
    today = datetime.date.today().isoformat()
    return ('_circulation.status:on_shelf AND '
            '_circulation.holdings.start_date:{0}->9999-01-01').format(today)


def items_on_loan_with_holds_query():
    today = datetime.date.today().isoformat()
    return ('_circulation.status:on_loan AND '
            '_circulation.holdings.start_date:{0}->9999-01-01').format(today)


def overdue_loans_with_holds_query():
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    return (
        '_circulation.status:on_loan AND '
        '_circulation.holdings.end_date:1970-01-01->{0}'
        '_circulation.holdings.start_date:{1}->9999-01-01'
    ).format(yesterday.isoformat(), today.isoformat())


CIRCULATION_LISTS = {
    'latest_loans': {
        'template': 'templates/invenio_circulation/lists/latest-loans.html',
        'query': latest_loans_query,
    },
    'overdue_loans': {
        'template': 'templates/invenio_circulation/lists/overdue-loans.html',
        'query': overdue_loans_query,
    },
    'items_on_shelf_with_holds': {
        'template': ('templates/invenio_circulation/lists/'
                     'items-on-shelf-with-holds.html'),
        'query': items_on_shelf_with_holds_query,
    },
    'items_on_loan_with_holds': {
        'template': ('templates/invenio_circulation/lists/'
                     'items-on-loan-with-holds.html'),
        'query': items_on_loan_with_holds_query,
    },
    'overdue_loans_with_holds': {
        'template': ('templates/invenio_circulation/lists/'
                     'overdue-loans-with-holds.html'),
        'query': overdue_loans_with_holds_query,
    },
}
