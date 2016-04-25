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

import pytest
from invenio_circulation import InvenioCirculation

from utils import (_create_dates, _create_test_data, _delete_test_data,
                   current_app, rec_uuids, state)


def test_loan_items_success_no_waitlist(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        clcs = api.circulation.loan_items(cu, [ci],
                                          start_date, end_date, False)

        clc = clcs[0]
        assert len(clcs) == 1
        assert clc.user == cu
        assert clc.item == ci
        assert clc.current_status == models.CirculationLoanCycle.STATUS_ON_LOAN
        assert clc.start_date == start_date
        assert clc.end_date == end_date
        assert clc.desired_start_date == start_date
        assert clc.desired_end_date == end_date

        _delete_test_data(cl, clr, clrm, cu, clc, ci)


def test_loan_items_failure_bad_user(current_app, rec_uuids):
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        try:
            api.circulation.loan_items(None, [ci],
                                       start_date, end_date, False)
            msg = 'loan_items should not work without a user.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        try:
            api.circulation.loan_items([cu], [ci],
                                       start_date, end_date, False)
            msg = 'loan_items should not work with multiple users.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        try:
            api.circulation.loan_items('user', [ci],
                                       start_date, end_date, False)
            msg = ('loan_items should only work with '
                   'invenio_circulation.models.CirculationUser.')
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_loan_items_failure_bad_item(current_app, rec_uuids):
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        try:
            api.circulation.loan_items(cu, None,
                                       start_date, end_date, False)
            msg = 'loan_items should not work without an item.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        try:
            api.circulation.loan_items(cu, ci,
                                       start_date, end_date, False)
            msg = 'loan_items should not work with a non-list item.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        try:
            api.circulation.loan_items(cu, ['item'],
                                       start_date, end_date, False)
            msg = ('loan_items should only work with '
                   'invenio_circulation.models.CirculationItem.')
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_loan_items_failure_start_date(current_app, rec_uuids):
    """
    The start date is not valid: the loan_items function only works for
    today.
    """
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        # The start_date starts tomorrow, which is not allowed in a loan
        start_date, end_date = _create_dates(start_days=1)

        try:
            api.circulation.loan_items(cu, [ci],
                                       start_date, end_date, False)
            msg = 'loan_items should not work with a future date'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        # The start_date starts yesterday, which is not allowed in a loan
        start_date, end_date = _create_dates(start_days=-1)

        try:
            api.circulation.loan_items(cu, [ci],
                                       start_date, end_date, False)
            msg = 'loan_items should not work with a past date'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_loan_items_failure_loan_period(current_app, rec_uuids):
    """
    The desired loan period exceeds the allowed period.
    """
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        # Loan period of 5 weeks
        start_date, end_date = _create_dates(end_weeks=8)

        try:
            api.circulation.loan_items(cu, [ci],
                                       start_date, end_date, False)
            msg = 'loan_items should not work with a loan period of 5 weeks'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_loan_items_failure_failed_date_suggestion(current_app, rec_uuids):
    """
    The date suggestion for a loan is not valid, since it doesn't start with
    today.
    """
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(end_weeks=2)

        clcs = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2, False)

        try:
            clcs += api.circulation.loan_items(cu, [ci],
                                               start_date1, end_date1, True)
            msg = 'loan_items should not work when the date is blocked'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, clcs[0], ci)


def test_loan_items_failure_active_request_no_waitlist(current_app, rec_uuids):
    """
    Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, so the loan fails.
    """
    import invenio_circulation.api as api
    import invenio_circulation.models as models
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(start_weeks=2)

        clcs = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2, False)

        try:
            clcs += api.circulation.loan_items(cu, [ci],
                                               start_date1, end_date1, False)
            msg = 'loan_items should not work when the date is blocked'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        assert len(clcs) == 1
        assert ci.current_status == models.CirculationItem.STATUS_ON_SHELF

        _delete_test_data(cl, clr, clrm, cu, clcs[0], ci)


def test_loan_items_success_active_request_waitlist(current_app, rec_uuids):
    """
    Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, but with the waitlist flag, the loan comes
    through. The end_date will be adjusted.
    """
    import datetime
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(start_weeks=2)

        clcs = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2, False)

        clcs += api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1, True)

        clc = clcs[1]
        assert len(clcs) == 2
        assert ci.current_status == models.CirculationItem.STATUS_ON_LOAN
        assert clc.start_date == start_date1
        assert clc.desired_start_date == start_date1
        assert clc.end_date == start_date2 - datetime.timedelta(days=1)
        assert clc.desired_end_date == end_date1

        _delete_test_data(cl, clr, clrm, cu, clcs[0], clcs[1], ci)


def test_request_items_success(current_app, rec_uuids):
    """
    Simplest case: The item is available for request and requested in the
    future.
    """
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates(start_weeks=2)

        clcs = api.circulation.request_items(cu, [ci],
                                             start_date, end_date, False)

        clc = clcs[0]
        stat = models.CirculationLoanCycle.STATUS_REQUESTED
        assert len(clcs) == 1
        assert clc.user == cu
        assert clc.item == ci
        assert clc.current_status == stat
        assert clc.start_date == start_date
        assert clc.end_date == end_date
        assert clc.desired_start_date == start_date
        assert clc.desired_end_date == end_date

        _delete_test_data(cl, clr, clrm, cu, clcs[0], ci)


def test_request_items_failure_bad_item(current_app, rec_uuids):
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        try:
            api.circulation.request_items(cu, None,
                                          start_date, end_date, False)
            msg = 'loan_items should not work without an item.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_request_items_failure_item_wrong_status(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        ci.current_status = models.CirculationItem.STATUS_MISSING

        try:
            api.circulation.request_items(cu, [ci],
                                          start_date, end_date, False)
            msg = 'loan_items should not work without an item.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_request_items_failure_bad_user(current_app, rec_uuids):
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        try:
            api.circulation.request_items(None, [ci],
                                          start_date, end_date, False)
            msg = 'loan_items should not work without a user.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_request_items_failure_start_date(current_app, rec_uuids):
    """
    The start date is not valid: the request_items function only works for
    today and future dates.
    """
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates(start_days=-1)

        try:
            api.circulation.request_items(cu, [ci],
                                          start_date, end_date, False)
            raise AssertionError('The requested start_date is in the past.')
        except Exception as e:
            assert type(e) == ValidationExceptions


def test_request_items_failure_loan_period(current_app, rec_uuids):
    """
    The desired loan period exceeds the allowed period.
    """
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates(end_weeks=8)

        try:
            api.circulation.request_items(cu, [ci],
                                          start_date, end_date, False)
            raise AssertionError('The requested loan period is too long.')
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_request_items_failure_active_request_no_waitlist(current_app,
                                                          rec_uuids):
    """
    Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, so the loan fails.
    """
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(start_weeks=2)

        clcs = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2, False)

        try:
            clcs += api.circulation.request_items(cu, [ci],
                                                  start_date1, end_date1,
                                                  False)
            raise AssertionError('The requested date is already taken')
        except Exception as e:
            type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, clcs[0], ci)


def test_request_items_success_active_request_waitlist(current_app, rec_uuids):
    """
    Request an item in the future, the status should therefore stay as
    'on_shelf' and the item should be loan-able.
    Since the request is two weeks in advance, the usual loan period of
    four weeks intersects, but with the waitlist flag, the loan comes
    through. The end_date will be adjusted.
    """
    import datetime
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(start_weeks=2)

        clcs = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2, False)

        clcs += api.circulation.request_items(cu, [ci],
                                              start_date1, end_date1, True)

        clc = clcs[1]
        assert len(clcs) == 2
        assert ci.current_status == models.CirculationItem.STATUS_ON_SHELF
        assert clc.start_date == start_date1
        assert clc.desired_start_date == start_date1
        assert clc.end_date == start_date2 - datetime.timedelta(days=1)
        assert clc.desired_end_date == end_date1

        _delete_test_data(cl, clr, clrm, cu, clcs[0], clcs[1], ci)


def test_return_items_successful(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        clcs = api.circulation.loan_items(cu, [ci],
                                          start_date, end_date, False)

        api.circulation.return_items([ci])

        clc = clcs[0]
        stat_finished = models.CirculationLoanCycle.STATUS_FINISHED
        assert len(clcs) == 1
        assert ci.current_status == models.CirculationItem.STATUS_ON_SHELF
        assert clc.current_status == stat_finished

        _delete_test_data(cl, clr, clrm, cu, clcs[0], ci)


def test_return_items_failure(current_app, rec_uuids):
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        try:
            api.circulation.return_items([ci])
            msg = 'return_items should not work with status on_shelf.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        try:
            api.circulation.return_items(None)
            msg = 'return_items should not work without items.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci)


def test_return_items_successful_update_waitlist1(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(start_weeks=2)

        # Loan the item first
        clcs = api.circulation.loan_items(cu, [ci],
                                          start_date1, end_date1, False)

        # Request the item another time, adding it to a waitlist
        clcs.extend(api.circulation.request_items(cu, [ci],
                                                  start_date2, end_date2,
                                                  True))

        clc1, clc2 = clcs[0], clcs[1]

        # Check the start dates of clc2
        assert clc2.desired_start_date == start_date2
        assert clc2.start_date == end_date1 + datetime.timedelta(days=1)

        # Return the item
        api.circulation.return_items([ci])

        # Check the start dates of clc2
        assert clc2.desired_start_date == start_date2
        assert clc2.start_date == start_date2

        _delete_test_data(cl, clr, clrm, cu, clc1, clc2, ci)
