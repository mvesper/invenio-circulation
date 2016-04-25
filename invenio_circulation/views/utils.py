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

"""invenio-circulation interface utilities."""

import datetime
import json
import inspect

import invenio_circulation.models as models

from flask import request
from dateutil import relativedelta


def send_signal(signal, sender, data):
    """Utility function to send a signal and process the returning data.

    This function works as an entrance point to handle signals, as it provides
    a way to overwrite and sort the results.

    :param signal: The signal to be send.
    :param sender: The sender.
    :param data: The data processed by the signal listener.
    :return: The results of the listeners.
    """
    res = {x[1]['name']: x[1] for x in signal.send(sender, data=data)}

    to_block = []
    for value in res.values():
        if 'misc' in value:
            for val in value:
                if val['action'] == 'block':
                    to_block.append(val['target'])

    for name in to_block:
        try:
            del res[name]
        except KeyError:
            pass

    return [x['result']
            for x in sorted(res.values(), key=lambda x: x.get('priority', 0.5))
            if x['result'] is not None]


def extract_params(func):
    """Extract parameters for a given flask endpoint function.

    Read the function parameters and extract the corresponding values from
    the flask.request object.
    """
    _args = inspect.getargspec(func).args

    def wrap():
        data = json.loads(request.get_json())
        return func(**{arg_name: data[arg_name] for arg_name in _args})

    wrap.func_name = func.func_name
    return wrap


def datetime_serial(obj):
    """JSON utility function to serialize datetime objects."""
    if isinstance(obj, datetime.date):
        return obj.isoformat()


def get_date_period(start_date, days):
    """Get start_date and end_date given a start_date and a number of days."""
    return start_date, start_date + datetime.timedelta(days=days)


def filter_params(func, **kwargs):
    """Extract parameters from keyword-arguments for a given function.

    Read the function parameters and extract the corresponding values from
    the given keyword-arguments.
    """
    import inspect
    return func(**{arg: kwargs[arg] for arg in inspect.getargspec(func).args})


def _get_cal_heatmap_dates(items):
    def to_seconds(date):
        return int(date.strftime("%s"))

    def get_date_range(start_date, end_date):
        delta = (end_date - start_date).days
        res = []
        for day in range(delta+1):
            res.append(start_date + datetime.timedelta(days=day))
        return res

    res = set()
    for item in items:
        query = 'item_id:{0}'.format(item.id)
        statuses = [models.CirculationLoanCycle.STATUS_FINISHED,
                    models.CirculationLoanCycle.STATUS_CANCELED]
        clcs = models.CirculationLoanCycle.search(query)
        clcs = filter(lambda x: x.current_status not in statuses, clcs)
        for clc in clcs:
            date_range = get_date_range(clc.start_date, clc.end_date)
            for date in date_range:
                res.add((str(to_seconds(date)), 1))

    return dict(res)


def _get_cal_heatmap_range(items):
    min_dates = []
    max_dates = []
    for item in items:
        query = 'item_id:{0}'.format(item.id)
        statuses = [models.CirculationLoanCycle.STATUS_FINISHED,
                    models.CirculationLoanCycle.STATUS_CANCELED]
        clcs = models.CirculationLoanCycle.search(query)
        clcs = filter(lambda x: x.current_status not in statuses, clcs)
        if not clcs:
            continue
        min_dates.append(min(clc.start_date for clc in clcs))
        max_dates.append(max(clc.end_date for clc in clcs))

    if not min_dates or not max_dates:
        return 0

    min_date = min(min_dates)
    max_date = max(max_dates)

    return relativedelta.relativedelta(max_date, min_date).months + 1


def flatten(l):
    """Flatten a single nested list."""
    return [x for sublist in l for x in sublist]


def get_user(current_user):
    """Get the invenio-circulation User corresponding to flask.current_user.

    If the user doesn't exist, create one using data provided by CERN-LDAP.
    """
    from invenio_circulation.signals import get_circulation_user_info

    try:
        # There is a CirculationUser corresponding to the current_user
        query = 'invenio_user_id:{0} OR email:{1}'.format(current_user.id,
                                                          current_user.email)
        user = models.CirculationUser.search(query)[0]
        if user.invenio_user_id is None:
            user.invenio_user_id = current_user.id
            user.save()
    except IndexError:
        user = send_signal(get_circulation_user_info, None,
                           current_user.email)[0]
        user.invenio_user_id = current_user.id
        user.save()

    return user
