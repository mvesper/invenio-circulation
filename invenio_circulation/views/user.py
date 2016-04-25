# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""invenio-circulation user interface."""

import datetime
import json

import invenio_circulation.api as api
import invenio_circulation.models as models

from invenio_circulation.views.utils import (
        datetime_serial, flatten, _get_cal_heatmap_dates,
        _get_cal_heatmap_range, send_signal, get_user)
from invenio_circulation.api.utils import ValidationExceptions

from flask import Blueprint, render_template, request, flash


blueprint = Blueprint('circulation_user', __name__, url_prefix='/circulation',
                      template_folder='../templates',
                      static_folder='../static')


@blueprint.route('/user', methods=['GET'])
@blueprint.route('/user/', methods=['GET'])
def users_current_holds():
    """User interface showing the current users holds."""
    from flask_login import current_user
    from invenio_circulation.signals import user_current_holds

    try:
        user = get_user(current_user)
    except AttributeError:
        # Anonymous User
        return render_template('invenio_theme/401.html')

    editor_schema = json.dumps(user._json_schema, default=datetime_serial)
    editor_data = json.dumps(user.jsonify(), default=datetime_serial)

    holds = send_signal(user_current_holds, 'user_current_holds', user.id)

    return render_template('user/user_overview.html',
                           editor_data=editor_data,
                           editor_schema=editor_schema,
                           holds=flatten(holds))


@blueprint.route('/user/record/<record_id>', methods=['GET'])
@blueprint.route('/user/record/<record_id>/<state>', methods=['GET'])
def user_record_actions(record_id, state=None):
    """User interface providing user interactions on a given record."""
    from flask_login import current_user

    try:
        user = get_user(current_user)
    except AttributeError:
        user = None

    record = models.CirculationRecord.get(record_id)

    start_date, end_date, waitlist, delivery = _get_state(state)

    record._items = _get_record_items(record_id, user,
                                      start_date, end_date,
                                      waitlist)

    cal_range = _get_cal_heatmap_range(x['item'] for x in record._items)
    cal_range = max(cal_range, (end_date.month - start_date.month + 1))

    return render_template('user/user_record_actions.html',
                           user=user, record=record,
                           start_date=start_date.isoformat(),
                           end_date=end_date.isoformat(),
                           waitlist=waitlist, delivery=delivery,
                           cal_range=cal_range, cal_data={})


@blueprint.route('/api/user/run_action', methods=['POST'])
def api_user_run_action():
    """API to run a specified user action on a hold."""
    from flask_login import current_user
    from invenio_circulation.signals import run_action, convert_params
    from invenio_circulation.api.utils import ValidationExceptions
    from invenio_circulation.views.utils import get_user

    data = json.loads(request.get_json())

    # We restrict the possibilities a bit
    if data['action'] not in ['request', 'loan_extension', 'cancel_clcs']:
        return ('', 500)

    try:
        user = get_user(current_user)
    except AttributeError:
        return ('', 500)

    res = send_signal(convert_params, data['action'], data)
    for key, value in reduce(lambda x, y: dict(x, **y), res).items():
        data[key] = value

    data['user'] = user

    try:
        message = send_signal(run_action, data['action'], data)[0]
    except ValidationExceptions:
        flash(('The desired action failed, click *CHECK PARAMETERS* '
               'for more information.'), 'danger')
        return ('', 500)

    flash(message)
    return ('', 200)


def _get_state(state):
    if state:
        start_date, end_date, waitlist, delivery = state.split(':')
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        waitlist = True if waitlist == 'true' else False
    else:
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(weeks=4)
        waitlist = False
        delivery = 'Pick up'

    return start_date, end_date, waitlist, delivery


def _get_record_items(record_id, user, start_date, end_date, waitlist):
    items = []
    query = 'record_id:{0}'.format(record_id)

    for item in models.CirculationItem.search(query):
        warnings = []
        try:
            api.circulation.try_request_items(user=user, items=[item],
                                              start_date=start_date,
                                              end_date=end_date,
                                              waitlist=waitlist)
            request = True
        except ValidationExceptions as e:
            exceptions = [x[0] for x in e.exceptions]
            if exceptions == ['date_suggestion'] and waitlist:
                request = True
            else:
                request = False
                for category, exception in e.exceptions:
                    warnings.append((category, exception.message))

        items.append({'item': item,
                      'request': request,
                      'cal_data': json.dumps(_get_cal_heatmap_dates([item])),
                      'cal_range': _get_cal_heatmap_range([item]),
                      'warnings': json.dumps(warnings)})

    return items
