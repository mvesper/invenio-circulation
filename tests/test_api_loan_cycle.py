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


def _create_loan_cycle(item, user, current_status=None,
                       start_date=None, end_date=None, delivery=None):
    if not start_date and not end_date:
        start_date, end_date = _create_dates()
    if not current_status:
        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
    if not delivery:
        delivery = models.CirculationLoanCycle.DELIVERY_DEFAULT
    return api.loan_cycle.create(item=item, user=user,
                                 current_status=current_status,
                                 start_date=start_date,
                                 end_date=end_date,
                                 desired_start_date=start_date,
                                 desired_end_date=end_date,
                                 delivery=delivery)


def test_loan_cycle_create(db, app, user, item):
    start_date, end_date = _create_dates()
    current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
    delivery = models.CirculationLoanCycle.DELIVERY_DEFAULT
    clc = _create_loan_cycle(item, user, current_status, start_date, end_date,
                             delivery)
    db.session.commit()

    assert clc
    assert clc['local_data']['item'] == item
    assert clc['local_data']['user'] == user
    assert clc['local_data']['current_status'] == current_status
    assert clc['local_data']['start_date'] == start_date
    assert clc['local_data']['end_date'] == end_date
    assert clc['local_data']['delivery'] == delivery

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')

    res = models.CirculationLoanCycle.search('uuid:{0}'.format(clc['uuid']))

    assert len(res) == 1
    assert res[0] == clc


def test_loan_cycle_update(db, app, user, item):
    clc = _create_loan_cycle(item, user)
    db.session.commit()

    assert clc['local_data'][
        'delivery'] == models.CirculationLoanCycle.DELIVERY_DEFAULT
    clc['local_data']['delivery'] = 'foo'
    clc.commit()
    db.session.commit()
    assert clc['local_data']['delivery'] == 'foo'

    clc = models.CirculationLoanCycle.get_record(clc['uuid'])
    assert clc['local_data']['delivery'] == 'foo'


def test_loan_cycle_delete(db, app, user, item):
    clc = _create_loan_cycle(item, user)
    db.session.commit()

    uuid = clc['uuid']
    clc.delete()
    db.session.commit()

    try:
        models.CirculationLoanCycle.get_record(uuid)
        raise AssertionError('The item should not exist.')
    except Exception:
        pass


def test_loan_cycle_cancel(db, app, user, item):
    clc = _create_loan_cycle(item, user)
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc])
    db.session.commit()

    clc = models.CirculationLoanCycle.get_record(clc['uuid'])

    status = models.CirculationLoanCycle.STATUS_CANCELED
    assert clc['local_data']['current_status'] == status


def test_loan_cycle_cancel_failure(db, app, user, item):
    current_status = models.CirculationLoanCycle.STATUS_FINISHED
    clc = _create_loan_cycle(item, user, current_status=current_status)
    db.session.commit()

    try:
        api.loan_cycle.cancel_clcs([clc])
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_overdue(db, app, user, item):
    start_date, end_date = _create_dates(start_weeks=-5)
    current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
    clc = _create_loan_cycle(item, user, current_status=current_status,
                             start_date=start_date, end_date=end_date)
    db.session.commit()

    api.loan_cycle.overdue_clcs([clc])
    db.session.commit()

    clc = models.CirculationLoanCycle.get_record(clc['uuid'])
    stat1 = models.CirculationLoanCycle.STATUS_ON_LOAN
    stat2 = models.CirculationLoanCycle.STATUS_OVERDUE
    assert clc['local_data']['current_status'] == stat1
    assert stat2 in clc['local_data']['additional_statuses']


def test_loan_cycle_overdue_failure(db, app, user, item):
    # The LoanCycle is in the wrong status
    current_status = models.CirculationLoanCycle.STATUS_FINISHED
    clc = _create_loan_cycle(item, user, current_status=current_status)
    db.session.commit()

    try:
        api.loan_cycle.overdue_clcs([clc])
        raise AssertionError('Overdue should not work with a LC on shelf.')
    except Exception as e:
        assert type(e) == ValidationExceptions

    # The end date is fine
    clc['local_data'][
        'current_status'] = models.CirculationLoanCycle.STATUS_ON_LOAN
    try:
        api.loan_cycle.overdue_clcs([clc])
        msg = 'Overdue should not work with a valid end date.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions

    # The LoanCycle is already overdue
    clc['local_data'][
        'end_date'] = datetime.date.today() - datetime.timedelta(days=1)
    stat = models.CirculationLoanCycle.STATUS_OVERDUE
    clc['local_data']['additional_statuses'].append(stat)
    try:
        api.loan_cycle.overdue_clcs([clc])
        msg = 'Overdue should not work when the LC is already overdue.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_extension(db, app, user, item):
    start_date, end_date = _create_dates(end_weeks=2)
    requested_end_date = end_date + datetime.timedelta(weeks=1)
    clc = _create_loan_cycle(item, user,
                             start_date=start_date, end_date=end_date)
    db.session.commit()

    api.loan_cycle.loan_extension([clc], requested_end_date)
    db.session.commit()

    clc = models.CirculationLoanCycle.get_record(clc['uuid'])

    assert clc['local_data']['end_date'] == requested_end_date


def test_loan_cycle_extension_failure_date_taken(db, app, user, item):
    start_date1, end_date1 = _create_dates(end_weeks=1)
    start_date2, end_date2 = _create_dates(start_weeks=2)
    requested_end_date = end_date1 + datetime.timedelta(weeks=2)

    clc_l = api.circulation.loan_items(user, [item],
                                       start_date1, end_date1)[0]
    db.session.commit()

    api.circulation.request_items(user, [item], start_date2, end_date2)[0]
    db.session.commit()

    try:
        api.loan_cycle.loan_extension([clc_l], requested_end_date)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_extension_failure_date_duration(db, app, user, item):
    start_date1, end_date1 = _create_dates(end_weeks=1)
    requested_end_date = end_date1 + datetime.timedelta(weeks=4)

    clc_l = api.circulation.loan_items(user, [item],
                                       start_date1, end_date1)[0]
    db.session.commit()

    try:
        api.loan_cycle.loan_extension([clc_l], requested_end_date)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_extension_failure_different_users(db, app, record,
                                                      location, user):
    item = api.item.create(record, location, 'isbn', 'barcode',
                           'shelf_number', 'description',
                           models.CirculationItem.STATUS_ON_SHELF,
                           models.CirculationItem.GROUP_BOOK)
    item1 = api.item.create(record, location, 'isbn', 'barcode',
                            'shelf_number', 'description',
                            models.CirculationItem.STATUS_ON_SHELF,
                            models.CirculationItem.GROUP_BOOK)

    from invenio_accounts.models import User
    from invenio_userprofiles import UserProfile

    user1 = User(email='jane.doe@mail.com', password='123456')
    up = UserProfile(username='Jane', full_name='Jane Doe')
    user1.profile = up
    db.session.add(user)
    db.session.add(up)
    db.session.commit()

    start_date1, end_date1 = _create_dates(end_weeks=1)
    requested_end_date = end_date1 + datetime.timedelta(weeks=1)

    clc_l = api.circulation.loan_items(user, [item],
                                       start_date1, end_date1)[0]
    db.session.commit()

    item1 = models.CirculationItem.get_record(item1['uuid'])

    clc_l1 = api.circulation.loan_items(user1, [item1],
                                        start_date1, end_date1)[0]
    db.session.commit()

    try:
        api.loan_cycle.loan_extension([clc_l, clc_l1], requested_end_date)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_extension_failure_item_status(db, app, user, item):
    start_date1, end_date1 = _create_dates(end_weeks=1)
    requested_end_date = end_date1 + datetime.timedelta(weeks=1)
    clc_l = api.circulation.loan_items(user, [item],
                                       start_date1, end_date1)[0]
    clc_l['current_status'] = models.CirculationLoanCycle.STATUS_FINISHED
    clc_l.commit()
    db.session.commit()

    clc_l = models.CirculationLoanCycle.get_record(clc_l['uuid'])

    try:
        api.loan_cycle.loan_extension([clc_l], requested_end_date)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_transform_into_loan(db, app, user, item):
    start_date, end_date = _create_dates()
    clc = api.circulation.request_items(user, [item],
                                        start_date, end_date)[0]
    db.session.commit()

    api.loan_cycle.transform_into_loan([clc])
    db.session.commit()

    clc = models.CirculationLoanCycle.get_record(clc['uuid'])
    assert clc['local_data'][
               'current_status'] == models.CirculationLoanCycle.STATUS_ON_LOAN


def test_loan_cycle_transform_into_loan_failure(db, app, user, item):
    start_date, end_date = _create_dates()
    clc = api.circulation.request_items(user, [item],
                                        start_date, end_date)[0]
    db.session.commit()

    try:
        api.loan_cycle.transform_into_loan([])
    except Exception as e:
        assert type(e) == ValidationExceptions

    clc['local_data'][
        'current_status'] = models.CirculationLoanCycle.STATUS_ON_LOAN
    try:
        api.loan_cycle.transform_into_loan([clc])
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_loan_cycle_transform_into_loan_failure_start_date(db, app,
                                                           user, item):
    start_date, end_date = _create_dates(start_weeks=1)
    clc = api.circulation.request_items(user, [item],
                                        start_date, end_date)[0]
    db.session.commit()

    try:
        api.loan_cycle.transform_into_loan([clc])
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_update_waitlist_starts_before_ends_before(db, app, user, item):
    # Starts before, ends before
    # present:          |-----|
    # requested: |----|
    start_date1, end_date1 = _create_dates(start_weeks=5)
    start_date2, end_date2 = _create_dates()

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2


def test_update_waitlist_starts_before_ends_in(db, app, user, item):
    # Starts before, ends in
    # present:          |-----|
    # requested:  |----|???
    start_date1, end_date1 = _create_dates(start_weeks=1)
    start_date2, end_date2 = _create_dates()

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2


def test_update_waitlist_starts_before_ends_after(db, app, user, item):
    # Starts before, ends after
    # present:          |-----|
    # requested:  |----|?????????
    start_date1, end_date1 = _create_dates(start_weeks=1, end_weeks=1)
    start_date2, end_date2 = _create_dates()

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2


def test_update_waitlist_starts_before_ends_in_other(db, app, user, item):
    # Starts before, ends in another
    # present:          |-----||----|
    # requested:  |----|?????????
    start_date1, end_date1 = _create_dates(start_weeks=1, end_weeks=1)
    start_date2, end_date2 = _create_dates(start_weeks=3)
    start_date3, end_date3 = _create_dates()

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2)[0]
    db.session.commit()

    clc3 = api.circulation.request_items(user, [item],
                                         start_date3, end_date3,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])
    clc3 = models.CirculationLoanCycle.get_record(clc3['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2
    assert clc3['local_data']['start_date'] == clc3[
        'local_data']['desired_start_date'] == start_date3
    assert clc3['local_data']['end_date'] == clc2[
        'local_data']['start_date'] - datetime.timedelta(days=1)
    assert clc3['local_data']['desired_end_date'] == end_date3


def test_update_waitlist_starts_before_ends_after_other(db, app, user, item):
    # Starts before, ends after another
    # present:          |-----||----|
    # requested:  |----|??????????????
    start_date1, end_date1 = _create_dates(start_weeks=1, end_weeks=1)
    start_date2, end_date2 = _create_dates(start_days=1, start_weeks=2,
                                           end_weeks=1)
    start_date3, end_date3 = _create_dates()

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2)[0]
    db.session.commit()

    clc3 = api.circulation.request_items(user, [item],
                                         start_date3, end_date3,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])
    clc3 = models.CirculationLoanCycle.get_record(clc3['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2
    assert clc3['local_data']['start_date'] == clc3[
        'local_data']['desired_start_date'] == start_date3
    assert clc3['local_data']['end_date'] == clc2[
        'local_data']['start_date'] - datetime.timedelta(days=1)
    assert clc3['local_data']['desired_end_date'] == end_date3


def test_update_waitlist_starts_after_end_after(db, app, user, item):
    # Starts after, ends after
    # present:   |-----|
    # requested:         |----|
    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=5)

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2


def test_update_waitlist_starts_in_ends_after(db, app, user, item):
    # Starts in, ends after
    # present:   |-----|
    # requested:     ???|----|
    start_date1, end_date1 = _create_dates()
    start_date2, end_date2 = _create_dates(start_weeks=1)

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2


def test_update_waitlist_starts_in_other_end_after(db, app, user, item):
    # Starts in anoter, ends after
    # present:   |-2-||--1--|
    # requested:   ??????????|--3-|
    start_date1, end_date1 = _create_dates(start_weeks=1, end_weeks=1)
    start_date2, end_date2 = _create_dates(end_days=6, end_weeks=0)
    start_date3, end_date3 = _create_dates(start_days=1)

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2)[0]
    db.session.commit()

    clc3 = api.circulation.request_items(user, [item],
                                         start_date3, end_date3,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])
    clc3 = models.CirculationLoanCycle.get_record(clc3['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2
    assert clc3['local_data']['start_date'] == clc2[
        'local_data']['end_date'] + datetime.timedelta(days=1)
    assert clc3['local_data']['desired_start_date'] == start_date3
    assert clc3['local_data']['end_date'] == clc3[
        'local_data']['desired_end_date'] == end_date3


def test_update_waitlist_update_two_no_overlap(db, app, user, item):
    # Starts in, ends after
    # Starts before, ends in
    # no overlap between the request
    # present:        |--1--|
    # requested:         ????|-2-|
    # requested: |-3-|???
    start_date1, end_date1 = _create_dates(start_weeks=1)
    start_date2, end_date2 = _create_dates(start_weeks=3)
    start_date3, end_date3 = _create_dates(end_weeks=2)

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2,
                                         waitlist=True)[0]
    db.session.commit()

    clc3 = api.circulation.request_items(user, [item],
                                         start_date3, end_date3,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])
    clc3 = models.CirculationLoanCycle.get_record(clc3['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2
    assert clc3['local_data']['start_date'] == clc3[
        'local_data']['desired_start_date'] == start_date3
    assert clc3['local_data']['end_date'] == clc3[
        'local_data']['desired_end_date'] == end_date3


def test_update_waitlist_update_two_overlap(db, app, user, item):
    # Starts in, ends after
    # Starts before, ends in
    # overlap between the request
    # present:        |--1--|
    # requested:         ????|-2-|
    # requested: |-3-|????
    start_date1, end_date1 = _create_dates(start_weeks=1, end_weeks=2)
    start_date2, end_date2 = _create_dates(start_days=10)
    start_date3, end_date3 = _create_dates(end_weeks=2)

    clc1 = api.circulation.request_items(user, [item],
                                         start_date1, end_date1)[0]
    db.session.commit()

    clc2 = api.circulation.request_items(user, [item],
                                         start_date2, end_date2,
                                         waitlist=True)[0]
    db.session.commit()

    clc3 = api.circulation.request_items(user, [item],
                                         start_date3, end_date3,
                                         waitlist=True)[0]
    db.session.commit()

    api.loan_cycle.cancel_clcs([clc1])
    db.session.commit()

    clc1 = models.CirculationLoanCycle.get_record(clc1['uuid'])
    clc2 = models.CirculationLoanCycle.get_record(clc2['uuid'])
    clc3 = models.CirculationLoanCycle.get_record(clc3['uuid'])

    assert clc1['local_data']['start_date'] == clc1[
        'local_data']['desired_start_date'] == start_date1
    assert clc1['local_data']['end_date'] == clc1[
        'local_data']['desired_end_date'] == end_date1
    assert clc2['local_data']['start_date'] == clc2[
        'local_data']['desired_start_date'] == start_date2
    assert clc2['local_data']['end_date'] == clc2[
        'local_data']['desired_end_date'] == end_date2
    assert clc3['local_data']['start_date'] == clc3[
        'local_data']['desired_start_date'] == start_date3
    assert clc3['local_data']['end_date'] == clc2[
        'local_data']['start_date'] - datetime.timedelta(days=1)
    assert clc3['local_data']['desired_end_date'] == end_date3
