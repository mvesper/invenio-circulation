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

"""invenio-circulation receiver to handle circulation signals."""

from invenio_circulation.signals import (circulation_current_state,
                                         circulation_search,
                                         circulation_state,
                                         circulation_actions,
                                         circulation_main_actions)


def _circulation_current_state(sender, data):
    def _get_circulation_state(search_string):
        # <item_ids>:<user_ids>:<record_ids>:<s_date>:<e_date>:<waitlist>:<delivery>:<search_string>
        import datetime
        from invenio_circulation.views.utils import get_date_period
        from invenio_circulation.config import DEFAULT_LOAN_PERIOD

        if not search_string:
            start_date, end_date = get_date_period(datetime.date.today(),
                                                   DEFAULT_LOAN_PERIOD)
            return [], [], [], start_date, end_date, False, 'Pick up', ''

        (item_ids, user_ids, record_ids,
         start_date, end_date,
         waitlist, delivery, search) = search_string.split(':', 7)

        item_ids = item_ids.split(',') if item_ids else []
        user_ids = user_ids.split(',') if user_ids else []
        record_ids = record_ids.split(',') if record_ids else []

        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        waitlist = True if waitlist.lower() == 'true' else False

        return (item_ids, user_ids, record_ids,
                start_date, end_date, waitlist, delivery, search)

    (item_ids, user_ids, record_ids,
     start_date, end_date,
     waitlist, delivery, search) = _get_circulation_state(data)

    data = {'item_ids': item_ids, 'user_ids': user_ids,
            'record_ids': record_ids,
            'start_date': start_date, 'end_date': end_date,
            'waitlist': waitlist, 'delivery': delivery, 'search': search}

    return {'name': 'circulation', 'result': data}


def _circulation_search(sender, data):
    def wrapped():
        import invenio_circulation.models as models
        from invenio_circulation.views.utils import send_signal
        from invenio_circulation.signals import get_circulation_user_info

        search = data['search']
        item_ids = data['item_ids']
        user_ids = data['user_ids']
        record_ids = data['record_ids']

        items = models.CirculationItem.search(search)
        records = models.CirculationRecord.search(search)
        users = models.CirculationUser.search(search)

        # Try to get a user from somewhere else
        if not users:
            try:
                users = [send_signal(get_circulation_user_info,
                                     None, search)[0]]
            except Exception:
                pass

        if items and records:
            items = []

        item_ids += [str(x.id) for x in items]
        record_ids += [str(x.id) for x in records]
        user_ids += [str(x.id) for x in users]
        start_date = data['start_date']
        end_date = data['end_date']
        waitlist = data['waitlist']
        delivery = data['delivery']

        search = ''

        return ':'.join([','.join(item_ids), ','.join(user_ids),
                         ','.join(record_ids),
                         start_date.isoformat(), end_date.isoformat(),
                         str(waitlist), delivery, search])

    return {'name': 'circulation', 'result': wrapped}


def _circulation_state(sender, data):
    def wrapped():
        import json
        import datetime
        import invenio_circulation.models as m
        from flask import render_template
        from invenio_circulation.receivers.utils import _try_action
        from invenio_circulation.views.utils import (
                _get_cal_heatmap_dates, _get_cal_heatmap_range)

        def _enhance_record_data(records):
            q = 'record_id:{0}'
            for record in records:
                record.items = m.CirculationItem.search(q.format(record.id))
                for item in record.items:
                    item.cal_data = json.dumps(_get_cal_heatmap_dates([item]))
                    item.cal_range = _get_cal_heatmap_range([item])

        def _get_warnings(validity, categories):
            res = []
            for action, messages in validity:
                try:
                    for category, message in messages:
                        if category in categories:
                            res.append((action, message))
                except (TypeError, ValueError):
                    pass

            return res

        def _get_global_cal_range(items, end_date):
            def _get_latest_end_date(items):
                query = 'item_id:{0}'
                func = m.CirculationLoanCycle.search
                return [x.end_date for item in items for x
                        in func(query.format(item.id))]
            try:
                latest_end_date = max(_get_latest_end_date(items))
            except ValueError:
                latest_end_date = end_date

            latest_end_date = max(latest_end_date, end_date)
            return latest_end_date.month - datetime.date.today().month + 1

        users = [m.CirculationUser.get(x) for x in data['user_ids']]
        items = [m.CirculationItem.get(x) for x in data['item_ids']]
        records = [m.CirculationRecord.get(x) for x in data['record_ids']]
        start_date = data['start_date']
        end_date = data['end_date']
        waitlist = data['waitlist']
        delivery = data['delivery']

        _enhance_record_data(records)

        data['user'] = users[0] if (users and len(users) == 1) else users
        data['items'] = items
        data['records'] = records

        _actions = [('LOAN', 'loan'), ('REQUEST', 'request'),
                    ('RETURN', 'return')]
        validity = [(action, _try_action(action, data)['result'])
                    for _, action in _actions]

        item_warnings = _get_warnings(validity, ['items_status'])
        date_warnings = _get_warnings(validity,
                                      ['start_date', 'date_suggestion'])

        global_cal_data = json.dumps(_get_cal_heatmap_dates(items))
        global_cal_range = _get_global_cal_range(items, end_date)

        return render_template('circulation/circulation_content.html',
                               active_nav='circulation',
                               items=items, users=users, records=records,
                               start_date=start_date, end_date=end_date,
                               # action_buttons=action_buttons,
                               cal_data=global_cal_data,
                               cal_range=global_cal_range,
                               waitlist=waitlist, delivery=delivery,
                               item_warnings=item_warnings,
                               date_warnings=date_warnings)

    return {'name': 'circulation', 'result': wrapped}


def _circulation_actions(sender, data):
    return {'name': 'circulation',
            'result': [('LOAN', 'loan'),
                       ('REQUEST', 'request'),
                       ('RETURN', 'return')]}


def _circulation_main_actions(sender, data):
    from invenio_circulation.receivers.utils import _try_action

    def _check(action):
        def _c(val):
            ignore = [('items', 'A item is required to loan an item.'),
                      ('user', 'A user is required to loan an item.')]
            for x in val:
                if x in ignore:
                    return None

            return all(map(lambda x: x is True, val))

        if action is True or action is False or action is None:
            return action
        else:
            return _c(action) if len(action) > 0 else None

    _actions = [('LOAN', 'loan'), ('REQUEST', 'request'),
                ('RETURN', 'return')]
    validity = [(action, _try_action(action, data)['result'])
                for _, action in _actions]
    action_buttons = [(name, action, _check(val))
                      for (name, action), (_, val)
                      in zip(_actions, validity)]

    return {'name': 'circulation', 'result': action_buttons}


circulation_current_state.connect(_circulation_current_state)
circulation_search.connect(_circulation_search)
circulation_state.connect(_circulation_state)
circulation_actions.connect(_circulation_actions, 'circulation_actions')
circulation_main_actions.connect(_circulation_main_actions)
