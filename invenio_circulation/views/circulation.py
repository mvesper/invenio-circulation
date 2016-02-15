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

"""Circulation interface."""

import json

from flask import Blueprint, render_template, request, redirect, flash

from invenio_circulation.views.utils import send_signal, flatten
from invenio_circulation.acl import circulation_admin_permission as cap


blueprint = Blueprint('circulation', __name__, url_prefix='/circulation',
                      template_folder='../templates',
                      static_folder='../static')


@blueprint.route('/', methods=['GET'])
@blueprint.route('/circulation/<search_string>', methods=['GET'])
@cap.require(403)
def circulation_search(search_string=None):
    from invenio_circulation.signals import circulation_current_state

    data = send_signal(circulation_current_state, None, search_string)[0]

    if data['search']:
        from invenio_circulation.signals import circulation_search

        new_url = send_signal(circulation_search, None, data)[0]()
        tmp = ':'.join(search_string.split(':')[:-1]) + ':'
        if new_url.lower() == tmp.lower():
            msg = 'Your search "{0}" did not match any results.'
            flash(msg.format(data['search']), 'warning')

        return redirect('/circulation/circulation/' + new_url)
    else:
        from invenio_circulation.signals import (circulation_state,
                                                 circulation_main_actions,
                                                 circulation_other_actions)

        content = send_signal(circulation_state, None, data)[0]()
        main_actions = flatten(send_signal(circulation_main_actions, None, data))
        other_actions = flatten(send_signal(circulation_other_actions, None, data))
        return render_template('circulation/circulation.html',
                               active_nav='circulation', content=content,
                               main_actions=main_actions,
                               other_actions=other_actions)


@blueprint.route('/api/circulation/run_action', methods=['POST'])
@cap.require(403)
def api_circulation_run_action():
    from invenio_circulation.signals import run_action, convert_params
    from invenio_circulation.api.utils import ValidationExceptions

    data = json.loads(request.get_json())

    res = send_signal(convert_params, data['action'], data)
    for key, value in reduce(lambda x, y: dict(x, **y), res).items():
        data[key] = value

    try:
        message = send_signal(run_action, data['action'], data)[0]
    except ValidationExceptions:
        flash(('The desired action failed, click *CHECK PARAMETERS* '
               'for more information.'), 'danger')
        return ('', 500)

    flash(message)
    return ('', 200)


@blueprint.route('/api/circulation/try_action', methods=['POST'])
@cap.require(403)
def api_circulation_try_action():
    from invenio_circulation.signals import try_action, convert_params

    data = json.loads(request.get_json())

    res = send_signal(convert_params, data['action'], data)
    for key, value in reduce(lambda x, y: dict(x, **y), res).items():
        data[key] = value

    return json.dumps(send_signal(try_action, data['action'], data)[0])
