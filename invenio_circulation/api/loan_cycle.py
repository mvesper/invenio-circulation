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

"""invenio-circulation api responsible for CirculationLoanCycle handling."""

import datetime

import invenio_circulation.models as models
from invenio_circulation.api.checks import (check_already_overdue,
                                            check_loan_cycle_statuses,
                                            check_loan_duration,
                                            check_loan_period_extension,
                                            check_multiple_users,
                                            check_overdue,
                                            check_transform_start_date)
from invenio_circulation.api.utils import (DateManager, ValidationExceptions,
                                           email_notification, run_checks)
from invenio_circulation.config import CIRCULATION_EMAILS_SENDER as CES
from invenio_circulation.signals import (circulation_loan_cycle_canceled,
                                         circulation_loan_cycle_created,
                                         circulation_loan_cycle_deleted,
                                         circulation_loan_cycle_extended,
                                         circulation_loan_cycle_overdued,
                                         circulation_loan_cycle_transformed,
                                         circulation_loan_cycle_updated)
from invenio_circulation.transaction import persist, persistent_context


@persist
def create(item, user, current_status, delivery, start_date, end_date,
           desired_start_date, desired_end_date,
           additional_statuses=None, requested_extension_end_date=None,
           group_uuid=None):
    """Create a CirculationLoanCycle object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    additional_statuses = additional_statuses if additional_statuses else []

    data = {'local_data': dict(
                item=item, user=user, current_status=current_status,
                additional_statuses=additional_statuses, delivery=delivery,
                start_date=start_date, end_date=end_date,
                desired_start_date=desired_start_date,
                desired_end_date=desired_end_date,
                requested_extension_end_date=requested_extension_end_date,
                group_uuid=group_uuid)}

    clc = models.CirculationLoanCycle.create(data)

    return clc


def try_cancel_clcs(clcs):
    """Check the conditions to cancel the loan cycles.

    Checked conditions:
    * The current_status must be 'on_shelf' or 'requested'.

    :raise: ValidationExceptions
    """
    params = dict(loan_cycles=clcs,
                  statuses=[models.CirculationLoanCycle.STATUS_REQUESTED,
                            models.CirculationLoanCycle.STATUS_ON_LOAN])
    funcs = [('loan_cycle_status', check_loan_cycle_statuses)]

    run_checks(funcs, params)


def cancel_clcs(clcs, reason=''):
    """Cancel the given loan cycles.

    The items current_status will be set to 'canceled'.
    This also calls api.loan_cycle.update_waitlist.
    :raise: ValidationExceptions
    """
    try:
        try_cancel_clcs(clcs)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for clc in clcs:
            clc['local_data']['current_status'] = models.CirculationLoanCycle.STATUS_CANCELED
            clc.commit()

            data = dict(loan_cycle=clc, reason=reason)
            circulation_loan_cycle_canceled.send(data)

            update_waitlist(clc)


def _get_involved_clcs(handled_clc, other_clcs):
    res = []
    statuses = [models.CirculationLoanCycle.STATUS_FINISHED,
                models.CirculationLoanCycle.STATUS_CANCELED]
    for clc in other_clcs:
        _issued_date = clc['local_data']['issued_date'] >= handled_clc['local_data']['issued_date']
        _status = clc['local_data']['current_status'] not in statuses
        _id = clc['uuid'] != handled_clc['uuid']
        if _issued_date and _status and _id:
            res.append(clc)
    return res


def _get_affected_clcs(handled_clc, involved_clcs):
    key_dsd = 'desired_start_date'
    key_ded = 'desired_end_date'
    start_date = handled_clc['local_data']['start_date']
    end_date = handled_clc['local_data']['end_date']
    involved_clcs = sorted(involved_clcs, key=lambda x: x['local_data']['issued_date'])
    res = []
    for clc in involved_clcs:
        if start_date <= clc['local_data']['desired_start_date'] <= end_date:
            # present:      |-----|
            # requested:        ???|---|
            # requested:     ?????
            # start_date affected
            res.append(clc)
        elif start_date <= clc['local_data']['desired_end_date'] <= end_date:
            # present:      |-----|
            # requested: |-|????
            # end_date affected
            res.append(clc)
        elif (clc['local_data'][key_dsd] <= start_date <= clc['local_data'][key_ded] and
              clc['local_data'][key_dsd] <= end_date <= clc['local_data'][key_ded]):
            # present:          |-----|
            # requested:    |--|???????????
            # requested:    ???????????|--|
            res.append(clc)
    return res


@persist
def update_waitlist(clc):
    """Update a virtual waitlist for a given loan cycle.

    This function will check all loan cycles occurring in the same period of
    time and update their start_date and end_date attributes if they differ
    from their desired_start_date and desired_end_date values if possible.
    """
    query = {'local_data.item.uuid': clc['local_data']['item']['uuid']}
    other_clcs = models.CirculationLoanCycle.mechanical_query(query)
    involved_clcs = _get_involved_clcs(clc, other_clcs)
    affected_clcs = _get_affected_clcs(clc, involved_clcs)

    if not affected_clcs:
        return

    for affected_clc in affected_clcs:
        _involved_clcs = involved_clcs[:]
        _involved_clcs.remove(affected_clc)

        start_date = affected_clc['local_data']['desired_start_date']
        end_date = affected_clc['local_data']['desired_end_date']
        requested_dates = [(lc['local_data']['start_date'], lc['local_data']['end_date'])
                           for lc in _involved_clcs]
        _start, _end = DateManager.get_contained_date(start_date, end_date,
                                                      requested_dates)

        _update = {}
        if _start < affected_clc['local_data']['start_date']:
            _update['start_date'] = _start

        if _end > affected_clc['local_data']['end_date']:
            _update['end_date'] = _end

        if _update:
            affected_clc['local_data'].update(_update)
            affected_clc.commit()

        user = affected_clc['local_data']['user']
        title = affected_clc['local_data']['item']['record']['title_statement']['title']
        email_notification('loan_updated', CES, user.email,
                           name=user.profile.full_name, title=title,
                           start_date=_start, end_date=_end)


def try_overdue_clcs(clcs):
    """Check the conditions to overdue the loan cycles.

    Checked conditions:
    * The current_status must be 'on_loan'.
    * The additional_statuses don't include 'overdue'.
    * The end_date attribute lays in the past.

    :raise: ValidationExceptions
    """
    params = dict(loan_cycles=clcs,
                  statuses=[models.CirculationLoanCycle.STATUS_ON_LOAN])
    funcs = [('loan_cycle_status', check_loan_cycle_statuses),
             ('loan_cycle_already_overdue', check_already_overdue),
             ('loan_cycle_overdue', check_overdue)]

    run_checks(funcs, params)


def overdue_clcs(clcs):
    """Overdue the given loan cycles.

    'overdue' will be added to the attribute additional_statuses.
    :raise: ValidationExceptions
    """
    try:
        try_overdue_clcs(clcs)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for clc in clcs:
            clc['local_data']['additional_statuses'].append(
                    models.CirculationLoanCycle.STATUS_OVERDUE)
            clc.commit()
            circulation_loan_cycle_overdued.send(clc)


def try_loan_extension(clcs, requested_end_date):
    """Check the conditions to extend the loan duration of the loan cycles.

    Checked conditions:
    * The current_status must be 'on_shelf'
    * The loan cycles must currently be associated with one user.
    * The user and the items are allowed to be extended.
    * The extended loan duration is valid.
    * The requested_end_date doesn't interfere with other loans/requests.

    :raise: ValidationExceptions
    """
    users = set(clc['local_data']['user'] for clc in clcs)
    user = list(users)[0]
    params = dict(loan_cycles=clcs, users=users, user=user,
                  items=[clc['local_data']['item'] for clc in clcs],
                  start_date=datetime.date.today(),
                  end_date=requested_end_date,
                  requested_end_date=requested_end_date,
                  statuses=[models.CirculationLoanCycle.STATUS_ON_LOAN])
    funcs = [('loan_cycle_status', check_loan_cycle_statuses),
             ('user', check_multiple_users),
             ('duration', check_loan_duration),
             ('date_suggestion', check_loan_period_extension)]

    run_checks(funcs, params)


def loan_extension(clcs, requested_end_date):
    """Extend the given loan cycles.

    'overdue' will be removed from the attribute additional_statuses.
    :raise: ValidationExceptions
    """
    new_end_date = requested_end_date
    try:
        try_loan_extension(clcs, requested_end_date)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for clc in clcs:
            try:
                clc['local_data']['additional_statuses'].remove(
                        models.CirculationLoanCycle.STATUS_OVERDUE)
            except ValueError:
                pass
            clc['local_data']['desired_end_date'] = requested_end_date
            clc['local_data']['end_date'] = new_end_date
            clc.commit()
            circulation_loan_cycle_extended.send(clc)


def try_transform_into_loan(clcs):
    """Check the conditions to transform the requests into loans.

    Checked conditions:
    * The current_status must be 'requested'.
    * The start_date must today or earlier.

    :raise: ValidationExceptions
    """
    params = dict(loan_cycles=clcs,
                  statuses=[models.CirculationLoanCycle.STATUS_REQUESTED])
    funcs = [('loan_cycle_status', check_loan_cycle_statuses),
             ('start_date', check_transform_start_date)]

    run_checks(funcs, params)


def transform_into_loan(clcs):
    """Transform the given requests into loans.

    The items current_status will be set to 'on_loan'.
    :raise: ValidationExceptions
    """
    try:
        try_transform_into_loan(clcs)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for clc in clcs:
            clc['local_data']['current_status'] = models.CirculationLoanCycle.STATUS_ON_LOAN
            clc.commit()
            circulation_loan_cycle_transformed.send(clc)
