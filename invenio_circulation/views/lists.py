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


@blueprint.route('/lists/<list_link>')
@cap.require(403)
def list_entrance(list_link):
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
