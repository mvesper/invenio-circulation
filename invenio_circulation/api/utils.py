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

"""invenio-circulation api utilities."""

from __future__ import absolute_import

import datetime
from itertools import starmap

from flask import current_app, render_template
from flask_mail import Message


def filter_params(func, **kwargs):
    """Extract parameters from keyword-arguments for a given function.

    Reads the function parameters and extracts the corresponding values from
    the given keyword-arguments.
    """
    import inspect
    return func(**{arg: kwargs[arg] for arg in inspect.getargspec(func).args})


def _exception_collect(exceptions, kind, func, params):
    try:
        filter_params(func, **params)
    except (AssertionError, DateException) as e:
        exceptions.append((kind, e))


def run_checks(funcs, params):
    """Run the given functions and collect AssertionErrors."""
    exceptions = []
    for kind, func in funcs:
        _exception_collect(exceptions, kind, func, params)

    if exceptions:
        raise ValidationExceptions(exceptions)


def email_notification(template_name, sender, receiver, **kwargs):
    """Send an email.

    :param template_name: The directory of header.msg and body.msg
    :param kwargs: The keyword arguments to use in the fetched template.
    """
    config = current_app.config
    ce = config['CIRCULATION_EMAILS'].get(template_name)

    if not ce:
        msg = 'The given template {0} does not exist'.format(template_name)
        raise Exception(msg)

    subject = render_template(ce + 'subject.msg', **kwargs)
    body = render_template(ce + 'body.msg', **kwargs)

    msg = Message(sender=sender, recipients=[receiver],
                  subject=subject, body=body)

    try:
        current_app.extensions['mail'].send(msg)
    except Exception:
        # FIXME
        pass


class DateException(Exception):
    """Exception occurring for overlapping date periods.

    Carries information of the dates involved in the overlap and possible
    alternatives.
    """

    def __init__(self, suggested_dates, contained_dates):
        """Constructor."""
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
        """String representation."""
        return self.message


class ValidationExceptions(Exception):
    """Exception to gather exceptions happening during api.try_* functions."""

    def __init__(self, exceptions):
        """Constructor."""
        self.exceptions = exceptions

    def __str__(self):
        """String representation."""
        return '\n'.join(['{0}: {1}'.format(x, str(y))
                          for x, y in self.exceptions])


class DateManager(object):
    """Utility class to calculate date confilcts."""

    _start = datetime.date(1970, 1, 1)

    @classmethod
    def _convert_to_days(cls, start_date, end_date):
        start_days = (start_date - cls._start).days
        end_days = (end_date - cls._start).days
        return start_days, end_days

    @classmethod
    def _convert_to_datetime(cls, start_days, end_days=None):
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
        for x in range(period_min, period_max+1):
            for start, end in periods:
                if start <= x <= end:
                    time_line.append(1)
                    break
            else:
                time_line.append(0)

        return period_min, time_line

    @classmethod
    def get_contained_date(cls, requested_start, requested_end, periods):
        """Get the dates contained in requested_start and requested_end.

        :param requested_start: The requested start date.
        :param requested_end: The requested end date.
        :param periods: The dates to be checked for conflicts.

        :return: Conflict free values for requested_start, requested_date.
        :raise: DateException with possible alternatives.
        """
        timeline_start, timeline = cls._build_timeline((requested_start,
                                                        requested_end),
                                                       periods)

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
        """Get available free periods in a list of periods.

        :return: A list of available periods.
        """
        if not periods:
            return [datetime.date.today()]
        today = datetime.date.today()
        timeline_start, timeline = cls._build_timeline((today, today), periods)

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
            res.append((timeline_start+len(timeline), None))

        return list(starmap(cls._convert_to_datetime, res))
