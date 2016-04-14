# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

import json

from flask import Blueprint, render_template

from invenio_circulation.views.utils import send_signal, flatten
from invenio_circulation.acl import circulation_admin_permission as cap

blueprint = Blueprint('lists', __name__, url_prefix='/circulation',
                      template_folder='../templates',
                      static_folder='../static')


@blueprint.route('/lists')
@cap.require(403)
def lists_overview():
    from invenio_circulation.signals import (
            lists_overview as _lists_overview)

    lists = flatten(send_signal(_lists_overview, 'lists_overview', None))
    return render_template('lists/overview.html',
                           active_nav='lists', lists=lists)


def _get_merged_headers(table_headers):
    # TODO: at some point using an OrderedSet seems to be a cleaner idea
    from collections import OrderedDict

    def merge(dict1, dict2):
        dict1.update(dict2)
        return dict1

    dicts = []
    for table_header in table_headers:
        tmp = OrderedDict()
        for column in table_header:
            tmp[column] = None
        dicts.append(tmp)

    merged_headers = reduce(merge, dicts, OrderedDict()).keys()

    return merged_headers


def _multiple_lists(list_links):
    from invenio_circulation.signals import lists_class

    clazzes = []
    for list_link in list_links:
        clazzes.append(send_signal(lists_class, list_link, None)[0])

    table_header = _get_merged_headers(clazz.table_header for clazz in clazzes)
    items = []
    for clazz in clazzes:
        for item in clazz.data():
            tmp = []
            for th in table_header:
                tmp.append(item['item'][th] if th in item['item'] else '')
            item['item'] = tmp
            items.append(item)


    modals = [('acquisition_vendor_price', 'Enter Vendor ID and price',
               [('vendor_id', 'Vendor ID'), ('price', 'Price')])]
    return render_template('lists/multiple_lists.html',
                           active_nav='lists',
                           table_header=table_header, items=items,
                           modals=modals)


@blueprint.route('/lists/<list_link>')
@cap.require(403)
def list_entrance(list_link):
    if ',' in list_link:
        return _multiple_lists(list_link.split(','))
    from invenio_circulation.signals import lists_class

    clazz = send_signal(lists_class, list_link, None)[0]
    return clazz.entrance()


@blueprint.route('/lists/<list_link>/detail/')
@blueprint.route('/lists/<list_link>/detail/<query>')
@cap.require(403)
def list_detail(list_link, query=None):
    from invenio_circulation.signals import lists_class

    clazz = send_signal(lists_class, list_link, None)[0]

    try:
        data = json.loads(query)
    except Exception:
        data = {}

    return clazz.detail(**data)
