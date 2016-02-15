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

"""invenio-circulation api responsible for api checks."""

import datetime

import invenio_circulation.models as models
from invenio_circulation.api.utils import DateException, DateManager
from invenio_circulation.config import CIRCULATION_LOAN_PERIOD as CLP


def check_loan_start(start_date):
    """Check that loan start_date is today.

    :raise: AssertionError
    """
    msg = 'For a loan, the start date must be today.'
    assert start_date == datetime.date.today(), msg


def check_request_start(start_date):
    """Check that request start_date is today or later.

    :raise: AssertionError
    """
    msg = 'For a loan, the start date must be today.'
    msg = 'To request, the start date must be today or later.'
    assert start_date >= datetime.date.today(), msg


def check_already_overdue(loan_cycles):
    """Check if given loan cycles are not overdue already.

    :raise: AssertionError
    """
    msg = 'The loan_cycles(s) {0} is/are already overdue.'

    _uuids = []

    s = models.CirculationLoanCycle.STATUS_OVERDUE
    for lc in loan_cycles:
        if s in lc['local_data']['additional_statuses']:
            _uuids.append(lc['uuid'])

    if _uuids:
        raise AssertionError(msg.format(', '.join(_uuids)))


def check_overdue(loan_cycles):
    """Check if given loan cycles are overdue.

    A loan cycle is overdue, if the *end_date* lies before today.

    :raise: AssertionError
    """
    today = datetime.date.today()
    msg = 'The loan_cycles(s) {0} is/are not overdue.'

    _uuids = []

    for lc in loan_cycles:
        if lc['local_data']['end_date'] > today:
            _uuids.append(lc['uuid'])

    if _uuids:
        raise AssertionError(msg.format(', '.join(_uuids)))


def check_multiple_users(users):
    """Check if there is one user.

    :raise: AssertionError
    """
    assert len(users) == 1


def check_transform_start_date(loan_cycles):
    """Check the *start_date* before transforming a request to a loan.

    In order to transform a request to a loan, the *start_date* must be today
    or later.

    :raise: AssertionError
    """
    msg = 'The requsted dates of {0} did not arrive yet. Requested at {1}.'
    today = datetime.date.today()

    _uuids, _dates = [], []
    for lc in loan_cycles:
        if lc['local_data']['start_date'] > today:
            _uuids.append(lc['uuid'])
            _dates.append(lc['local_data']['start_date'].isoformat())

    if _uuids:
        raise AssertionError(msg.format(', '.join(_uuids), ', '.join(_dates)))


def check_item_statuses(items, statuses):
    """Check that *current_status* of items is in statuses.

    :param items: List of items.
    :param statuses: List of potential statuses.
    :raise: AssertionError
    """
    msg = ('The item(s) {0} is/are in the wrong status: '
           'current: {1}, required: {2}')

    _barcodes, _statuses = [], []

    for item in items:
        if item['local_data']['current_status'] not in statuses:
            _barcodes.append(item['item_information_general_information']['piece_designation'])
            _statuses.append(item['local_data']['current_status'])

    if _barcodes:
        raise AssertionError(msg.format(', '.join(_barcodes),
                                        ', '.join(_statuses),
                                        ' or '.join(statuses)))


def check_loan_cycle_statuses(loan_cycles, statuses):
    """Check that *current_status* of loan_cyles is in statuses.

    :param items: List of loan cycles.
    :param statuses: List of potential statuses.
    :raise: AssertionError
    """
    msg = ('The loan_cycles(s) {0} is/are in the wrong status: '
           'current: {1}, required: {2}')

    _uuids, _statuses = [], []

    for lc in loan_cycles:
        if lc['local_data']['current_status'] not in statuses:
            _uuids.append(lc['uuid'])
            _statuses.append(lc['local_data']['current_status'])

    if _uuids:
        raise AssertionError(msg.format(', '.join(_uuids),
                                        ', '.join(_statuses),
                                        ' or '.join(statuses)))


def get_affected_loan_cycles(statuses, items):
    """Get all loan cyles with given statuses refering to the given items."""
    def filter_func(x):
        return x['local_data']['current_status'] not in statuses

    clc_list = [models.CirculationLoanCycle.mechanical_query(
                    {'local_data.item.uuid': item['uuid']})
                for item in items]
    clc_list = [item for sub_list in clc_list for item in sub_list]
    return filter(filter_func, clc_list)


def get_requested_dates(lcs):
    """Get *start_date* and *end_date* of the given loan_cycles."""
    return [(lc['local_data']['start_date'], lc['local_data']['end_date']) for lc in lcs]


def check_loan_period(user, items, start_date, end_date):
    """Check the requested loan period.

    If the requested loan_period conflicts with existing requests/loans, a
    DateException is raised with potential other dates, if there are any.

    :raise: DateException
    """
    lcs = get_affected_loan_cycles(['finished', 'canceled'], items)
    requested_dates = get_requested_dates(lcs)
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


def check_loan_period_extension(loan_cycles, requested_end_date):
    """Check if a loan extension is possible.

    :raise: DateException
    """
    _ids = [clc.id for clc in loan_cycles]
    items = [clc['local_data']['item'] for clc in loan_cycles]
    start_date = datetime.date.today()
    end_date = requested_end_date

    lcs = get_affected_loan_cycles(['finished', 'canceled'], items)
    lcs = filter(lambda x: x.id not in _ids, lcs)
    requested_dates = get_requested_dates(lcs)
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


def check_loan_duration(user, items, start_date, end_date):
    """Check the time period between *start_date* and *end_date*.

    :raise: AssertionError
    """
    desired_loan_period = end_date - start_date

    msg = ('The desired loan period ({0} days) exceeds '
           'the allowed period of {1} days.')
    msg = msg.format(desired_loan_period.days, CLP)

    assert desired_loan_period.days <= CLP, msg
