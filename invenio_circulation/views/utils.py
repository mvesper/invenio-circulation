import datetime
import json
import inspect

import invenio_circulation.models as models

from flask import request
from dateutil import relativedelta


def send_signal(signal, sender, data):
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
    _args = inspect.getargspec(func).args

    def wrap():
        data = json.loads(request.get_json())
        return func(**{arg_name: data[arg_name] for arg_name in _args})

    wrap.func_name = func.func_name
    return wrap


def datetime_serial(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()


def get_date_period(start_date, days):
    return start_date, start_date + datetime.timedelta(days=days)


def filter_params(func, **kwargs):
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
    return [x for sublist in l for x in sublist]
