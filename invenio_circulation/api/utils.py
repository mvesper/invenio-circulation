import datetime
import functools

from jinja2 import Template
from itertools import starmap
from difflib import SequenceMatcher
from flask import current_app
from flask_mail import Message

from invenio_circulation.models import (CirculationLoanCycle,
                                        CirculationMailTemplate,
                                        CirculationLoanRule,
                                        CirculationLoanRuleMatch)


def check_field_in(field_name, values, message):
    def wrapper(objs):
        def check(obj):
            return obj.__getattribute__(field_name) in values
        if not all(map(check, objs)):
            raise Exception(message)
    return wrapper


def check_field_op(field_name, operator, values, message, negate=False):
    def wrapper(objs):
        def check(obj):
            attr = obj.__getattribute__(field_name)
            oper = attr.__getattribute__(operator)
            if negate:
                return not oper(values)
            return oper(values)
        if not all(map(check, objs)):
            raise Exception(message)
    return wrapper


def try_functions(*funcs):
    def wrapper(**kwargs):
        exceptions = []
        for name, func in funcs:
            try:
                func(**kwargs)
            except Exception as e:
                exceptions.append((name, e))

        if exceptions:
            raise ValidationExceptions(exceptions)
    return wrapper


def _get_requested_dates(lcs):
    return [(lc.start_date, lc.end_date) for lc in lcs]


def _get_affected_loan_cycles(statuses, items):
    def filter_func(x):
        return x.current_status not in statuses
    # clc_list = [CirculationLoanCycle.search(item=item.id) for item in items]
    clc_list = [CirculationLoanCycle.search('item_id:{0}'.format(item.id))
                for item in items]
    clc_list = [item for sub_list in clc_list for item in sub_list]
    return filter(filter_func, clc_list)


def _check_loan_period(user, items, start_date, end_date):
    lcs = _get_affected_loan_cycles(['finished', 'canceled'], items)
    requested_dates = _get_requested_dates(lcs)
    _start, _end = DateManager.get_contained_date(start_date, end_date,
                                                  requested_dates)
    available_start_date = _start
    desired_start_date = start_date

    available_end_date = _end
    desired_end_date = end_date

    avd_start_date = available_start_date != desired_start_date
    avd_end_date = available_end_date != desired_end_date
    if avd_start_date or avd_end_date:
        suggested_dates = DateManager.get_date_suggestions(requested_dates)
        contained_dates = (_start, _end)
        raise DateException(suggested_dates=suggested_dates,
                            contained_dates=contained_dates)


def _check_loan_period_extension(clcs, requested_end_date):
    _ids = [clc.id for clc in clcs]
    items = [clc.item for clc in clcs]
    start_date = datetime.date.today()
    end_date = requested_end_date

    lcs = _get_affected_loan_cycles(['finished', 'canceled'], items)
    lcs = filter(lambda x: x.id not in _ids, lcs)
    requested_dates = _get_requested_dates(lcs)
    _start, _end = DateManager.get_contained_date(start_date, end_date,
                                                  requested_dates)
    available_start_date = _start
    desired_start_date = start_date

    available_end_date = _end
    desired_end_date = end_date

    avd_start_date = available_start_date != desired_start_date
    avd_end_date = available_end_date != desired_end_date
    if avd_start_date or avd_end_date:
        suggested_dates = DateManager.get_date_suggestions(requested_dates)
        contained_dates = (_start, _end)
        raise DateException(suggested_dates=suggested_dates,
                            contained_dates=contained_dates)


def _check_loan_duration(user, items, start_date, end_date):
    desired_loan_period = end_date - start_date
    allowed_loan_period = get_loan_period(user, items)
    if desired_loan_period.days > allowed_loan_period:
        msg = ('The desired loan period ({0} days) exceeds '
               'the allowed period of {1} days.')
        raise Exception(msg.format(desired_loan_period.days,
                                   allowed_loan_period))


def update(obj, **kwargs):
    current_items = {key: obj.__getattribute__(key) for key in dir(obj)
                     if not callable(obj.__getattribute__(key)) and not
                     key.startswith("__")}

    changed = {}

    for key, value in kwargs.items():
        if value != current_items[key]:
            try:
                obj.__setattr__(key, value)
            except Exception:
                pass
            changed[key] = value

    if changed:
        obj.save()

    return current_items, changed


def email_notification(template_name, sender, receiver, **kwargs):
    try:
        query = 'template_name:{0}'.format(template_name)
        cmt = CirculationMailTemplate.search(query)[0]
    except IndexError:
        return

    subject = Template(cmt.subject).render(**kwargs)
    header = Template(cmt.header).render(**kwargs)
    content = Template(cmt.content).render(**kwargs)

    body = '\n'.join([header, content])

    msg = Message(sender=sender, recipients=[receiver],
                  subject=subject, body=body)

    # TODO: socket exception ~.~
    try:
        current_app.extensions['mail'].send(msg)
    except Exception:
        print msg


def compare_query(library_code, item_type, user_group, rule):
    def _compare(val, rule_val):
        if '*' in rule_val:
            tmp = rule_val.replace('*', '')
            if val.startswith(tmp):
                res = SequenceMatcher(None, val, tmp).ratio()
                return res if res > 0 else 0.1  # This addresses '*'
        else:
            if rule_val == val:
                return 1
        return 0

    library_val = _compare(library_code, rule.location_code)
    item_val = _compare(item_type, rule.item_type)
    user_val = _compare(user_group, rule.patron_type)

    return (item_val, user_val, library_val, rule.loan_rule_id)


def get_loan_rule(user, item):
    user_group = user.user_group
    item_type = item.item_group
    library_code = item.location.code

    # Direct query
    query = 'user_group:{0} item_group:{1} location_code:{2}'
    query = query.format(user_group, item_type, library_code)

    rules = CirculationLoanRuleMatch.search(query)

    if not rules:
        comp = functools.partial(compare_query,
                                 library_code, item_type, user_group)
        rules = sorted([comp(x) for x in CirculationLoanRuleMatch.get_all()],
                       key=lambda x: (1-x[0], 1-x[1], 1-x[2]))
        rules = filter(lambda x: x[0] != 0 and x[1] != 0 and x[2] != 0, rules)

    rule = rules[0]

    return CirculationLoanRule.get(rule[3])


def get_loan_period(user, items):
    try:
        return max(get_loan_rule(user, item).loan_period for item in items)
    except ValueError:
        return 0


class DateException(Exception):
    def __init__(self, suggested_dates, contained_dates):
        self.suggested_dates = suggested_dates
        self.contained_dates = contained_dates

        if self.suggested_dates is None and self.contained_dates is None:
            msg = 'The date is already taken. There are no valid suggestions'
            self.message = msg
            return

        tmp = ['{0} - {1}'.format(start, end)
               for start, end in self.suggested_dates[:-1]]
        tmp.append('{0} - ...'.format(self.suggested_dates[-1]))
        self.message = 'The date is already taken, try: ' + ' or '.join(tmp)

    def __str__(self):
        return self.message


class ValidationExceptions(Exception):
    def __init__(self, exceptions):
        self.exceptions = exceptions

    def __str__(self):
        return '\n'.join(['{0}: {1}'.format(x, str(y))
                          for x, y in self.exceptions])


class DateManager(object):
    _start = datetime.date(1970, 1, 1)

    @classmethod
    def _convert_to_days(cls, start_date, end_date):
        start_days = (start_date - cls._start).days
        end_days = (end_date - cls._start).days
        return start_days, end_days

    @classmethod
    def _convert_to_datetime(cls, start_days, end_days):
        if end_days:
            return (cls._start + datetime.timedelta(days=start_days),
                    cls._start + datetime.timedelta(days=end_days))
        else:
            return cls._start + datetime.timedelta(days=start_days)

    @classmethod
    def _build_timeline(cls, requested_period, periods):
        periods = sorted(periods, key=lambda x: x[0])
        periods = list(starmap(cls._convert_to_days, periods))
        requested_period = cls._convert_to_days(*requested_period)
        periods_and_requested = periods + [requested_period]
        period_min = min(periods_and_requested, key=lambda x: x[0])[0]
        period_max = max(periods_and_requested, key=lambda x: x[1])[1]

        time_line = []
        for x in range(period_min, period_max):
            for start, end in periods:
                if start <= x <= end:
                    time_line.append(1)
                    break
            else:
                time_line.append(0)

        return period_min, time_line

    @classmethod
    def get_contained_date(cls, requested_start, requested_end, periods):
        try:
            timeline_start, timeline = cls._build_timeline((requested_start,
                                                            requested_end),
                                                           periods)
        except ValueError:
            return requested_start, requested_end

        req_start_day, req_end_day = cls._convert_to_days(requested_start,
                                                          requested_end)

        start_in_timeline = req_start_day - timeline_start
        end_in_timeline = req_end_day - timeline_start

        start, end = None, None

        for i, day in enumerate(timeline[start_in_timeline:end_in_timeline]):
            if day == 0:
                if start is None:
                    start = start_in_timeline+i
            elif day == 1:
                if start is not None and end is None:
                    end = start_in_timeline+i-1

        if start is None and end is None:
            raise DateException(None, None)
        elif start is not None and end is None:
            return cls._convert_to_datetime(timeline_start+start, req_end_day)
        else:
            return cls._convert_to_datetime(timeline_start+start,
                                            timeline_start+end)

    @classmethod
    def get_date_suggestions(cls, periods):
        if not periods:
            return [datetime.date.today()]
        today = datetime.date.today()
        try:
            timeline_start, timeline = cls._build_timeline((today, today),
                                                           periods)
        except ValueError:
            return []

        res = []
        start, end = None, None

        for i, day in enumerate(timeline):
            if day == 0:
                if start is None:
                    start = i
            elif day == 1:
                if start is not None and end is None:
                    end = i-1

            if start is not None and end is not None:
                res.append((timeline_start+start, timeline_start+end))
                start, end = None, None

        if start is None and end is None:
            res.append((timeline_start+len(timeline)+1, None))
        elif start is not None:
            res.append((timeline_start+start, timeline_start+len(timeline)))

        return list(starmap(cls._convert_to_datetime, res))
