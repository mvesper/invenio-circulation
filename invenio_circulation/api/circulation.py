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

"""invenio-circulation api responsible for the item circulation."""

import uuid

import invenio_circulation.models as models
from invenio_circulation.api.checks import (check_item_statuses,
                                            check_loan_duration,
                                            check_loan_period,
                                            check_loan_start,
                                            check_request_start)
from invenio_circulation.api.loan_cycle import create as create_lc
from invenio_circulation.api.loan_cycle import update_waitlist
from invenio_circulation.api.utils import (ValidationExceptions,
                                           email_notification, run_checks)
from invenio_circulation.config import CIRCULATION_EMAILS_SENDER as CES
from invenio_circulation.signals import (circulation_item_loaned,
                                         circulation_item_requested,
                                         circulation_item_returned)
from invenio_circulation.transaction import persist, persistent_context
from invenio_db import db


def try_loan_items(user, items, start_date, end_date,
                   waitlist=False, delivery=None):
    """Check the conditions to loan the given items to the given user.

    Checked conditions:
    * Item object is valid (not None).
    * Item is in a valid condition (current_status: on_loan).
    * User meets the requirements to loan the item.
    * Given dates are valid (not in the past, not in the future).
    * Duration is valid.

    :param items: List of CirculationItem.
    :param user: CirculationUser.
    :param start_date: Start date of the loan (without time).
    :param end_date: End date of the loan (without time).

    :raise: ValidationExceptions
    """
    params = dict(user=user, items=items, start_date=start_date,
                  end_date=end_date, waitlist=waitlist, delivery=delivery,
                  statuses=[models.CirculationItem.STATUS_ON_SHELF])
    funcs = [('item_status', check_item_statuses),
             ('start_date', check_loan_start),
             ('duration', check_loan_duration),
             ('loan_period', check_loan_period)]

    run_checks(funcs, params)


def loan_items(user, items, start_date, end_date,
               waitlist=False, delivery=None):
    """Loan given items to the user.

    :param items: List of CirculationItem.
    :param user: CirculationUser.
    :param start_date: Start date of the loan (without time).
    :param end_date: End date of the loan (without time).
    :param waitlist: If the desired dates are not available, the item will be
                     put on a waitlist.
    :param delivery: 'pick_up' or 'internal_mail'

    :return: List of created CirculationLoanCycles
    :raise: ValidationExceptions
    """
    try:
        try_loan_items(user, items, start_date, end_date, waitlist)
        desired_start_date = start_date
        desired_end_date = end_date
    except ValidationExceptions as e:
        if [x[0] for x in e.exceptions] == ['loan_period'] and waitlist:
            _start, _end = e.exceptions[0][1].contained_dates
            desired_start_date = start_date
            desired_end_date = end_date
            start_date = _start
            end_date = _end
            if _start != desired_start_date:
                raise e
        else:
            raise e

    if delivery is None:
        delivery = models.CirculationLoanCycle.DELIVERY_DEFAULT

    group_uuid = str(uuid.uuid4())
    res = []
    with persistent_context():
        for item in items:
            item['local_data'][
                'current_status'] = models.CirculationItem.STATUS_ON_LOAN
            item.commit()

            current_status = models.CirculationLoanCycle.STATUS_ON_LOAN

            clc = create_lc(
                item=item, user=user, current_status=current_status,
                additional_statuses=[], delivery=delivery,
                start_date=start_date, end_date=end_date,
                desired_start_date=desired_start_date,
                desired_end_date=desired_end_date,
                requested_extension_end_date=None,
                group_uuid=group_uuid)

            res.append(clc)

            circulation_item_loaned.send(clc)

    email_notification('item_loan', CES, user.email,
                       name=user.profile.full_name, action='loaned',
                       items=[x['record']['title_statement']['title']
                              for x in items])

    return res


def try_request_items(user, items, start_date, end_date,
                      waitlist=False, delivery=None):
    """Check the conditions to request the given items for the given user.

    Checked conditions:
    * Item object is valid (not None).
    * Item is in a valid condition (current_status: on_loan).
    * User meets the requirements to loan the item.
    * Given dates are valid (not in the past).
    * Duration is valid.

    :param items: List of CirculationItem.
    :param user: CirculationUser.
    :param start_date: Start date of the loan (without time).
    :param end_date: End date of the loan (without time).

    :raise: ValidationExceptions
    """
    params = dict(user=user, items=items, start_date=start_date,
                  end_date=end_date, waitlist=waitlist, delivery=delivery,
                  statuses=[models.CirculationItem.STATUS_ON_LOAN,
                            models.CirculationItem.STATUS_ON_SHELF])
    funcs = [('item_status', check_item_statuses),
             ('start_date', check_request_start),
             ('duration', check_loan_duration),
             ('loan_period', check_loan_period)]

    run_checks(funcs, params)


def request_items(user, items, start_date, end_date,
                  waitlist=False, delivery=None):
    """Request given items for the user.

    :param items: List of CirculationItem.
    :param user: CirculationUser.
    :param start_date: Start date of the loan (without time).
    :param end_date: End date of the loan (without time).
    :param waitlist: If the desired dates are not available, the item will be
                     put on a waitlist.
    :param delivery: 'pick_up' or 'internal_mail'

    :return: List of created CirculationLoanCycles
    :raise: ValidationExceptions
    """
    try:
        try_request_items(user, items, start_date, end_date, waitlist)
        desired_start_date = start_date
        desired_end_date = end_date
    except ValidationExceptions as e:
        if [x[0] for x in e.exceptions] == ['loan_period'] and waitlist:
            _start, _end = e.exceptions[0][1].contained_dates
            desired_start_date = start_date
            desired_end_date = end_date
            start_date = _start
            end_date = _end
        else:
            raise e

    if delivery is None:
        delivery = models.CirculationLoanCycle.DELIVERY_DEFAULT

    group_uuid = str(uuid.uuid4())
    res = []
    with persistent_context():
        for item in items:
            current_status = models.CirculationLoanCycle.STATUS_REQUESTED
            clc = create_lc(item=item, user=user,
                            current_status=current_status,
                            additional_statuses=[], delivery=delivery,
                            start_date=start_date, end_date=end_date,
                            desired_start_date=desired_start_date,
                            desired_end_date=desired_end_date,
                            requested_extension_end_date=None,
                            group_uuid=group_uuid)

            res.append(clc)

            circulation_item_requested.send(clc)

    email_notification('item_loan', CES, user.email,
                       name=user.profile.full_name, action='requested',
                       items=[x['record']['title_statement']['title']
                              for x in items])

    return res


def try_return_items(items):
    """Check the conditions to return the given items.

    Checked conditions:
    * Item is in a valid condition (current_status: on_loan).

    :param items: List of CirculationItem.

    :raise: ValidationExceptions
    """
    params = dict(items=items,
                  statuses=[models.CirculationItem.STATUS_ON_LOAN])
    funcs = [('item_status', check_item_statuses)]

    run_checks(funcs, params)


def return_items(items):
    """Return given items.

    :param items: List of CirculationItem.

    :return: List of created CirculationLoanCycles
    :raise: ValidationExceptions
    """
    try:
        try_return_items(items)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for item in items:
            item['local_data'][
                 'current_status'] = models.CirculationItem.STATUS_ON_SHELF
            item.commit()

            on_loan = models.CirculationLoanCycle.STATUS_ON_LOAN
            query = {'local_data.item.uuid': item['uuid'],
                     'local_data.current_status': on_loan}
            clc = models.CirculationLoanCycle.mechanical_query(query)[0]
            clc['local_data'][
                'current_status'] = models.CirculationLoanCycle.STATUS_FINISHED
            clc.commit()

            circulation_item_returned.send(clc)

            update_waitlist(clc)
