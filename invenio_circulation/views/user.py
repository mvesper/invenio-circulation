import datetime
import json

import invenio_circulation.api as api
import invenio_circulation.models as models

from invenio_circulation.views.utils import (datetime_serial,
                                             flatten,
                                             _get_cal_heatmap_dates,
                                             _get_cal_heatmap_range,
                                             send_signal)
from invenio_circulation.api.utils import ValidationExceptions

from flask import Blueprint, render_template


blueprint = Blueprint('user', __name__, url_prefix='/circulation',
                      template_folder='../templates',
                      static_folder='../static')


@blueprint.route('/user/<user_id>', methods=['GET'])
def users_current_holds(user_id):
    from invenio_circulation.signals import user_current_holds

    obj = models.CirculationUser.get(user_id)
    editor_data = json.dumps(obj.jsonify(), default=datetime_serial)
    editor_schema = json.dumps(obj._json_schema, default=datetime_serial)

    holds = send_signal(user_current_holds, 'user_current_holds', user_id)

    return render_template('user/user_overview.html',
                           editor_data=editor_data,
                           editor_schema=editor_schema,
                           holds=flatten(holds))


@blueprint.route('/user/<user_id>/record/<record_id>', methods=['GET'])
@blueprint.route('/user/<user_id>/record/<record_id>/<state>', methods=['GET'])
def user_record_actions(user_id, record_id, state=None):
    try:
        user = models.CirculationUser.get(user_id)
    except Exception:
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
