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

from __future__ import absolute_import, print_function

import datetime

from utils import _create_dates

import invenio_circulation.api as api
import invenio_circulation.models as models

from invenio_circulation.api.utils import ValidationExceptions


def test_loan_items_success_no_waitlist(db, app, user, item):
    start_date, end_date = _create_dates()
    clcs = api.circulation.loan_items(user, [item],
                                      start_date, end_date, False)
    db.session.commit()

    CLC = models.CirculationLoanCycle
    clc = clcs[0]
    assert len(clcs) == 1
    assert clc['local_data']['user'] == user
    assert clc['local_data']['item'] == item
    assert clc['local_data']['current_status'] == CLC.STATUS_ON_LOAN
    assert clc['local_data']['start_date'] == start_date
    assert clc['local_data']['end_date'] == end_date
    assert clc['local_data']['desired_start_date'] == start_date
    assert clc['local_data']['desired_end_date'] == end_date

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    assert CLC.search('uuid:{0}'.format(clc['uuid']))


def test_loan_items_failure_bad_item(app, user, item):
    start_date, end_date = _create_dates()
    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_ON_LOAN

    try:
        api.circulation.loan_items(user, [item],
                                   start_date, end_date, False)
        msg = 'loan_items should not work with status != on_shelf.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_items_failure_start_date(app, user, item):
    # The start date is not valid: the loan_items function only works for
    # today.
    start_date, end_date = _create_dates(start_days=1)

    try:
        api.circulation.loan_items(user, [item],
                                   start_date, end_date, False)
        msg = 'loan_items should not work with a future date'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions

    # The start_date starts yesterday, which is not allowed in a loan
    start_date, end_date = _create_dates(start_days=-1)

    try:
        api.circulation.loan_items(user, [item],
                                   start_date, end_date, False)
        msg = 'loan_items should not work with a past date'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_items_failure_loan_period(app, user, item):
    # The desired loan period exceeds the allowed period.
    start_date, end_date = _create_dates(end_weeks=8)

    try:
        api.circulation.loan_items(user, [item],
                                   start_date, end_date, False)
        msg = 'loan_items should not work with a loan period of 5 weeks'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_items_failure_failed_date_suggestion(db, app, user, item):
    # The date suggestion for a loan is not valid, since it doesn't start with
    # today.
    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(end_weeks=2)

    clcs = api.circulation.request_items(user, [item],
                                         start_date2, end_date2, False)
    db.session.commit()

    try:
        clcs += api.circulation.loan_items(user, [item],
                                           start_date1, end_date1, True)
        msg = 'loan_items should not work when the date is blocked'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_items_failure_active_request_no_waitlist(db, app, user, item):
    """ Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, so the loan fails.
    """

    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=2)

    clcs = api.circulation.request_items(user, [item],
                                         start_date2, end_date2, False)
    db.session.commit()

    try:
        clcs += api.circulation.loan_items(user, [item],
                                           start_date1, end_date1, False)
        msg = 'loan_items should not work when the date is blocked'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions

    assert len(clcs) == 1
    assert item['local_data'][
        'current_status'] == models.CirculationItem.STATUS_ON_SHELF


def test_loan_items_success_active_request_waitlist(db, app, user, item):
    """ Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, but with the waitlist flag, the loan comes
    through. The end_date will be adjusted.
    """

    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=2)

    clcs = api.circulation.request_items(user, [item],
                                         start_date2, end_date2, False)
    db.session.commit()

    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=2)

    clcs += api.circulation.loan_items(user, [item],
                                       start_date1, end_date1, True)
    db.session.commit()

    clc = clcs[1]
    assert len(clcs) == 2
    assert item['local_data'][
        'current_status'] == models.CirculationItem.STATUS_ON_LOAN
    assert clc['local_data']['start_date'] == start_date1
    assert clc['local_data']['desired_start_date'] == start_date1
    assert clc['local_data'][
               'end_date'] == start_date2 - datetime.timedelta(days=1)
    assert clc['local_data']['desired_end_date'] == end_date1


def test_request_items_success(db, app, user, item):
    """ Simplest case: The item is available for request and requested in the
    future.
    """

    start_date, end_date = _create_dates(start_weeks=2)
    clcs = api.circulation.request_items(user, [item],
                                         start_date, end_date, False)
    db.session.commit()

    clc = clcs[0]
    stat = models.CirculationLoanCycle.STATUS_REQUESTED
    assert len(clcs) == 1
    assert clc['local_data']['user'] == user
    assert clc['local_data']['item'] == item
    assert clc['local_data']['current_status'] == stat
    assert clc['local_data']['start_date'] == start_date
    assert clc['local_data']['end_date'] == end_date
    assert clc['local_data']['desired_start_date'] == start_date
    assert clc['local_data']['desired_end_date'] == end_date


def test_request_items_failure_item_wrong_status(app, user, item):
    start_date, end_date = _create_dates()

    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_MISSING

    try:
        api.circulation.request_items(user, [item],
                                      start_date, end_date, False)
        msg = 'loan_items should not work without an item.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_request_items_failure_start_date(app, user, item):
    """ The start date is not valid: the request_items function only works for
    today and future dates.
    """

    start_date, end_date = _create_dates(start_days=-1)

    try:
        api.circulation.request_items(user, [item],
                                      start_date, end_date, False)
        raise AssertionError('The requested start_date is in the past.')
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_request_items_failure_loan_period(app, user, item):
    """ The desired loan period exceeds the allowed period.
    """

    start_date, end_date = _create_dates(end_weeks=8)

    try:
        api.circulation.request_items(user, [item],
                                      start_date, end_date, False)
        raise AssertionError('The requested loan period is too long.')
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_request_items_failure_active_request_no_waitlist(db, app, user, item):
    """ Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, so the loan fails.
    """

    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=2)

    clcs = api.circulation.request_items(user, [item],
                                         start_date2, end_date2, False)
    db.session.commit()

    try:
        clcs += api.circulation.request_items(user, [item],
                                              start_date1, end_date1,
                                              False)
        raise AssertionError('The requested date is already taken')
    except Exception as e:
        type(e) == ValidationExceptions


def test_request_items_success_active_request_waitlist(db, app, user, item):
    """ Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, but with the waitlist flag, the loan comes
    through. The end_date will be adjusted.
    """

    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=2)

    clcs = api.circulation.request_items(user, [item],
                                         start_date2, end_date2, False)
    db.session.commit()

    clcs += api.circulation.request_items(user, [item],
                                          start_date1, end_date1, True)
    db.session.commit()

    clc = clcs[1]
    assert len(clcs) == 2
    assert item['local_data'][
                'current_status'] == models.CirculationItem.STATUS_ON_SHELF
    assert clc['local_data']['start_date'] == start_date1
    assert clc['local_data']['desired_start_date'] == start_date1
    assert clc['local_data'][
               'end_date'] == start_date2 - datetime.timedelta(days=1)
    assert clc['local_data']['desired_end_date'] == end_date1


def test_return_items_successful(db, app, user, item):
    start_date, end_date = _create_dates()

    clcs = api.circulation.loan_items(user, [item],
                                      start_date, end_date, False)
    db.session.commit()

    item = models.CirculationItem.get_record(item['uuid'])

    api.circulation.return_items([item])
    db.session.commit()

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    q = 'local_data.item.uuid:{0}'.format(item['uuid'])
    clcs = models.CirculationLoanCycle.search(q)

    clc = clcs[0]
    stat_finished = models.CirculationLoanCycle.STATUS_FINISHED
    assert len(clcs) == 1
    assert item['local_data'][
                'current_status'] == models.CirculationItem.STATUS_ON_SHELF
    assert clc['local_data']['current_status'] == stat_finished


def test_return_items_failure(app, user, item):
    start_date, end_date = _create_dates()

    try:
        api.circulation.return_items([item])
        msg = 'return_items should not work with status on_shelf.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_return_items_successful_update_waitlist1(db, app, user, item):
    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=2)

    # Loan the item first
    clcs = api.circulation.loan_items(user, [item],
                                      start_date1, end_date1, False)
    db.session.commit()

    # Request the item another time, adding it to a waitlist
    clcs.extend(api.circulation.request_items(user, [item],
                                              start_date2, end_date2,
                                              True))
    db.session.commit()

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    q = 'local_data.item.uuid:{0}'.format(item['uuid'])
    clcs = models.CirculationLoanCycle.search(q)
    clcs = sorted(clcs, key=lambda x: x['local_data']['issued_date'])
    clc = clcs[1]

    # Check the start dates of clc2
    assert clc['local_data']['desired_start_date'] == start_date2
    assert clc['local_data'][
               'start_date'] == end_date1 + datetime.timedelta(days=1)

    # Return the item
    item = models.CirculationItem.get_record(item['uuid'])
    api.circulation.return_items([item])
    db.session.commit()

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    q = 'local_data.item.uuid:{0}'.format(item['uuid'])
    clcs = models.CirculationLoanCycle.search(q)
    clcs = sorted(clcs, key=lambda x: x['local_data']['issued_date'])
    clc = clcs[1]

    # Check the start dates of clc2
    assert clc['local_data']['desired_start_date'] == start_date2
    assert clc['local_data']['start_date'] == start_date2
