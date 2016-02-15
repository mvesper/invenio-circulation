# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.


"""Module tests."""

import datetime
import random

from invenio_circulation.api.utils import DateException, DateManager


def test_convert_to_days():
    _start = datetime.date(1970, 1, 1)
    d = datetime.date.today()

    result = DateManager._convert_to_days(d, d)

    assert result[0] == (d - _start).days
    assert result[1] == (d - _start).days


def test_convert_to_datetime():
    d = datetime.date.today()
    days = DateManager._convert_to_days(d, d)
    dates = DateManager._convert_to_datetime(*days)

    assert len(dates) == 2
    assert dates[0] == d
    assert dates[1] == d

    date = DateManager._convert_to_datetime(days[0])
    assert date == d


def test_build_timeline_single_day():
    _start = datetime.date(1970, 1, 1)
    d = datetime.date.today()
    periods = []
    requested_period = (d, d)

    timeline_start, timeline = DateManager._build_timeline(requested_period,
                                                           periods)

    assert timeline_start == (d - _start).days
    assert len(timeline) == 1
    assert timeline[0] == 0


def test_build_timeline_reverse_dates():
    _start = datetime.date(1970, 1, 1)
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=10)
    periods = []
    requested_period = (d2, d1)

    timeline_start, timeline = DateManager._build_timeline(requested_period,
                                                           periods)

    assert timeline_start == (d2 - _start).days
    assert not timeline


def test_build_timeline_no_periods():
    _start = datetime.date(1970, 1, 1)
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=1)
    periods = []
    requested_period = (d1, d2)

    timeline_start, timeline = DateManager._build_timeline(requested_period,
                                                           periods)

    assert timeline_start == (d1 - _start).days
    assert len(timeline) == 2
    assert not any(timeline)


def test_build_timeline_period_at_end():
    _start = datetime.date(1970, 1, 1)
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=1)
    d3 = d1 + datetime.timedelta(days=2)
    d4 = d3 + datetime.timedelta(days=1)
    periods = [(d3, d4)]
    requested_period = (d1, d2)

    timeline_start, timeline = DateManager._build_timeline(requested_period,
                                                           periods)

    # import pdb; pdb.set_trace()
    assert timeline_start == (d1 - _start).days
    assert len(timeline) == 4
    assert not any(timeline[:2])
    assert all(timeline[2:])


def test_build_timeline_period_at_beginning():
    _start = datetime.date(1970, 1, 1)
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=1)
    d3 = d1 + datetime.timedelta(days=2)
    d4 = d3 + datetime.timedelta(days=1)
    periods = [(d1, d2)]
    requested_period = (d3, d4)

    timeline_start, timeline = DateManager._build_timeline(requested_period,
                                                           periods)

    # import pdb; pdb.set_trace()
    assert timeline_start == (d1 - _start).days
    assert len(timeline) == 4
    assert all(timeline[:2])
    assert not any(timeline[2:])


def test_build_timeline_random():
    _start = datetime.date(1970, 1, 1)
    outer_bound_start = datetime.date.today()
    outer_bound_end = outer_bound_start + datetime.timedelta(days=30)
    requested_period = (outer_bound_start, outer_bound_end)

    for _ in range(100):
        start_day = random.randint(0, 30)
        end_day = random.randint(start_day, 30)
        d1 = outer_bound_start + datetime.timedelta(days=start_day)
        d2 = outer_bound_start + datetime.timedelta(days=end_day)
        periods = [(d1, d2)]

        timeline_start, timeline = DateManager._build_timeline(
                requested_period, periods)

        assert timeline_start == (outer_bound_start - _start).days
        assert len(timeline) == 31
        assert not any(timeline[:start_day])
        assert all(timeline[start_day:end_day+1])
        assert not any(timeline[end_day+1:])


def test_get_contained_dates_no_periods():
    # requested:    |---|
    # periods:
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=1)
    periods = []

    start, end = DateManager.get_contained_date(d1, d2, periods)

    assert start == d1
    assert end == d2


def test_get_contained_dates_period_start():
    # requested:    |---|
    # periods:   |---|
    d1 = datetime.date.today() + datetime.timedelta(days=5)
    d2 = d1 + datetime.timedelta(days=10)
    d3 = datetime.date.today()
    d4 = d3 + datetime.timedelta(days=10)
    periods = [(d3, d4)]

    start, end = DateManager.get_contained_date(d1, d2, periods)

    assert start == d4 + datetime.timedelta(days=1)
    assert end == d2


def test_get_contained_dates_period_end():
    # requested:    |---|
    # periods:         |---|
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=10)
    d3 = d1 + datetime.timedelta(days=5)
    d4 = d3 + datetime.timedelta(days=10)
    periods = [(d3, d4)]

    start, end = DateManager.get_contained_date(d1, d2, periods)

    assert start == d1
    assert end == d3 - datetime.timedelta(days=1)


def test_get_contained_dates_period_both_ends():
    # requested:    |---|
    # periods:   |---| |---|
    d1 = datetime.date.today() + datetime.timedelta(days=5)
    d2 = d1 + datetime.timedelta(days=10)
    d3 = datetime.date.today()
    d4 = d1 + datetime.timedelta(days=2)
    d5 = d2 - datetime.timedelta(days=2)
    d6 = d5 + datetime.timedelta(days=10)
    periods = [(d3, d4), (d5, d6)]

    start, end = DateManager.get_contained_date(d1, d2, periods)

    assert start == d4 + datetime.timedelta(days=1)
    assert end == d5 - datetime.timedelta(days=1)


def test_get_contained_dates_period_inside():
    # requested:    |---|
    # periods:       |-|
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=10)
    d3 = d1 + datetime.timedelta(days=1)
    d4 = d2 - datetime.timedelta(days=1)
    periods = [(d3, d4)]

    start, end = DateManager.get_contained_date(d1, d2, periods)

    assert start == d1
    assert end == d1


def test_get_contained_dates_identical():
    # requested:    |---|
    # periods:      |---|
    d1 = datetime.date.today()
    d2 = d1 + datetime.timedelta(days=10)
    periods = [(d1, d2)]

    try:
        start, end = DateManager.get_contained_date(d1, d2, periods)
    except DateException as e:
        assert e.suggested_dates is None
        assert e.contained_dates is None


def test_get_date_suggestions_empty():
    # periods:
    periods = []

    suggestions = DateManager.get_date_suggestions(periods)

    assert len(suggestions) == 1
    assert suggestions[0] == datetime.date.today()


def test_get_date_suggestions_full():
    # periods: |---|
    d = datetime.date.today()
    periods = [(d, d)]

    suggestions = DateManager.get_date_suggestions(periods)

    assert len(suggestions) == 1
    assert type(suggestions[0]) == datetime.date
    assert suggestions[0] == d + datetime.timedelta(days=1)


def test_get_date_suggestions_future():
    # periods:  |---|
    d1 = datetime.date.today() + datetime.timedelta(days=2)
    periods = [(d1, d1)]

    suggestions = DateManager.get_date_suggestions(periods)

    assert len(suggestions) == 2
    assert len(suggestions[0]) == 2
    assert type(suggestions[1]) == datetime.date
    assert suggestions[0][0] == datetime.date.today()
    assert suggestions[0][1] == d1 - datetime.timedelta(days=1)
