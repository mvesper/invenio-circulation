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

from invenio_circulation.api.utils import (DateManager,
                                           DateException,
                                           ValidationExceptions,
                                           check_field_in,
                                           _check_loan_duration,
                                           _check_loan_period_extension,
                                           is_renewable)
from invenio_circulation.api.utils import update as _update
from invenio_circulation.api.event import create as create_event


def create(item_id, user_id, current_status, start_date, end_date,
           desired_start_date, desired_end_date, issued_date, delivery,
           group_uuid=None):
    """Create a CirculationLoanCycle object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    clc = models.CirculationLoanCycle.new(
            item_id=item_id, user_id=user_id,
            current_status=current_status,
            start_date=start_date, end_date=end_date,
            desired_start_date=desired_start_date,
            desired_end_date=desired_end_date,
            issued_date=issued_date,
            delivery=delivery,
            group_uuid=group_uuid)

    create_event(loan_cycle_id=clc.id,
                 event=models.CirculationLoanCycle.EVENT_CREATE)

    return clc


def update(clc, **kwargs):
    """Update a CirculationLoanCycle object."""
    current_items, changed = _update(clc, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]

        create_event(loan_cycle_id=clc.id,
                     event=models.CirculationLoanCycle.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(clc):
    """Delete a CirculationLoanCycle object."""
    create_event(loan_cycle_id=clc.id,
                 event=models.CirculationLoanCycle.EVENT_DELETE)
    clc.delete()


def try_cancel_clcs(clcs):
    """Check the conditions to cancel the loan cycles.

    Checked conditions:
    * The current_status must be 'on_shelf' or 'requested'.

    :raise: ValidationExceptions
    """
    exceptions = []

    try:
        statuses = [models.CirculationLoanCycle.STATUS_REQUESTED,
                    models.CirculationLoanCycle.STATUS_ON_LOAN]
        msg = 'Objects(s) is/are in the wrong status.'
        for clc in clcs:
            assert clc.current_status in statuses, msg
    except AssertionError as e:
        exceptions.append(('status', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


def cancel_clcs(clcs, reason=''):
    """Cancelt the given loan cycles.

    The items current_status will be set to 'on_shelf'.
    This also calls api.loan_cycle.update_waitlist.
    :raise: ValidationExceptions
    """
    try:
        try_cancel_clcs(clcs)
    except ValidationExceptions as e:
        raise e

    for clc in clcs:
        clc.current_status = models.CirculationLoanCycle.STATUS_CANCELED
        clc.save()
        create_event(loan_cycle_id=clc.id,
                     event=models.CirculationLoanCycle.EVENT_CANCELED,
                     description=reason)

        update_waitlist(clc)


def _get_involved_clcs(handled_clc, other_clcs):
    res = []
    statuses = [models.CirculationLoanCycle.STATUS_FINISHED,
                models.CirculationLoanCycle.STATUS_CANCELED]
    for clc in other_clcs:
        _issued_date = clc.issued_date >= handled_clc.issued_date
        _status = clc.current_status not in statuses
        _id = clc.id != handled_clc.id
        if _issued_date and _status and _id:
            res.append(clc)
    return res


def _get_affected_clcs(handled_clc, involved_clcs):
    start_date = handled_clc.start_date
    end_date = handled_clc.end_date
    involved_clcs = sorted(involved_clcs, key=lambda x: x.issued_date)
    res = []
    for clc in involved_clcs:
        if start_date <= clc.desired_start_date <= end_date:
            # present:      |-----|
            # requested:        ???|---|
            # requested:     ?????
            # start_date affected
            res.append(clc)
        elif start_date <= clc.desired_end_date <= end_date:
            # present:      |-----|
            # requested: |-|????
            # end_date affected
            res.append(clc)
        elif (clc.desired_start_date <= start_date <= clc.desired_end_date and
              clc.desired_start_date <= end_date <= clc.desired_end_date):
            # present:          |-----|
            # requested:    |--|???????????
            # requested:    ???????????|--|
            res.append(clc)
    return res


def update_waitlist(clc):
    """Update a virtual waitlist for a given loan cycle.

    This function will check all loan cycles occurring in the same period of
    time and update their start_date and end_date attributes if they differ
    from their desired_start_date and desired_end_date values if possible.
    """
    query = 'item_id:{0}'.format(clc.item.id)
    other_clcs = models.CirculationLoanCycle.search(query)
    involved_clcs = _get_involved_clcs(clc, other_clcs)
    affected_clcs = _get_affected_clcs(clc, involved_clcs)

    if not affected_clcs:
        return

    for affected_clc in affected_clcs:
        _involved_clcs = involved_clcs[:]
        _involved_clcs.remove(affected_clc)

        start_date = affected_clc.desired_start_date
        end_date = affected_clc.desired_end_date
        requested_dates = [(lc.start_date, lc.end_date)
                           for lc in _involved_clcs]
        _start, _end = DateManager.get_contained_date(start_date, end_date,
                                                      requested_dates)

        _update = {}
        if _start < affected_clc.start_date:
            _update['start_date'] = _start

        if _end > affected_clc.end_date:
            _update['end_date'] = _end

        if _update:
            update(affected_clc, **_update)
        # TODO: mail the other guy


def try_overdue_clcs(clcs):
    """Check the conditions to overdue the loan cycles.

    Checked conditions:
    * The current_status must be 'on_loan'.
    * The additional_statuses don't include 'overdue'.
    * The end_date attribute lays in the past.

    :raise: ValidationExceptions
    """
    exceptions = []

    try:
        assert clcs, 'There need to be LoanCycles.'
    except AssertionError as e:
        exceptions.append(('status', e))

    try:
        status = models.CirculationLoanCycle.STATUS_ON_LOAN
        msg = 'Objects(s) is/are in the wrong status.'
        for clc in clcs:
            assert clc.current_status == status, msg
    except AssertionError as e:
        exceptions.append(('status', e))

    try:
        status = models.CirculationLoanCycle.STATUS_OVERDUE
        msg = 'Objects(s) is/are already overdue.'
        for clc in clcs:
            assert status not in clc.additional_statuses, msg
    except AssertionError as e:
        exceptions.append(('status', e))

    try:
        today = datetime.date.today()
        msg = 'The LoanCycle(s) is/are not overdue.'
        for clc in clcs:
            assert clc.end_date < today
    except AssertionError as e:
        exceptions.append(('end_date', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


def overdue_clcs(clcs):
    """Overdue the given loan cycles.

    'overdue' will be added to the attribute additional_statuses.
    :raise: ValidationExceptions
    """
    try:
        try_overdue_clcs(clcs)
    except ValidationExceptions as e:
        raise e

    for clc in clcs:
        clc.additional_statuses.append(
                models.CirculationLoanCycle.STATUS_OVERDUE)
        clc.save()
        create_event(loan_cycle_id=clc.id,
                     event=models.CirculationLoanCycle.EVENT_OVERDUE)


def _extension_allowed(user, items):
    if not is_renewable(user, items):
        raise Exception('One of the items is not renewable.')


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
    start_date = datetime.date.today()
    users = set(clc.user for clc in clcs)
    items = [clc.item for clc in clcs]

    exceptions = []

    try:
        check_field_in('current_status',
                       [models.CirculationLoanCycle.STATUS_ON_LOAN],
                       'Object(s) is/are in the wrong state')(objs=clcs)
    except Exception as e:
        exceptions.append(('status', e))

    try:
        if len(users) > 1:
            raise Exception('Too many different users.')
        else:
            user = users.pop()
    except Exception as e:
        exceptions.append(('user', e))

    try:
        _extension_allowed(user, items)
    except Exception as e:
        exceptions.append(('extension_allowed', e))

    try:
        _check_loan_duration(user, items, start_date, requested_end_date)
    except Exception as e:
        exceptions.append(('duration', e))

    try:
        _check_loan_period_extension(clcs, requested_end_date)
    except DateException as e:
        exceptions.append(('date_suggestion', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


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

    for clc in clcs:
        try:
            clc.additional_statuses.remove(
                    models.CirculationLoanCycle.STATUS_OVERDUE)
        except ValueError:
            pass
        clc.desired_end_date = requested_end_date
        clc.end_date = new_end_date
        clc.save()
        create_event(loan_cycle_id=clc.id,
                     event=models.CirculationLoanCycle.EVENT_LOAN_EXTENSION)


def try_transform_into_loan(clcs):
    """Check the conditions to transform the requests into loans.

    Checked conditions:
    * The current_status must be 'requested'.
    * The start_date must today or earlier.

    :raise: ValidationExceptions
    """
    exceptions = []

    try:
        assert clcs, 'There need to be LoanCycles.'
    except AssertionError as e:
        exceptions.append(('status', e))

    try:
        status = models.CirculationLoanCycle.STATUS_REQUESTED
        msg = 'Objects(s) is/are in the wrong status.'
        for clc in clcs:
            assert clc.current_status == status, msg
    except AssertionError as e:
        exceptions.append(('status', e))

    try:
        today = datetime.date.today()
        msg = 'Objects(s) start date must be today or earlier.'
        for clc in clcs:
            assert clc.start_date <= today, msg
    except AssertionError as e:
        exceptions.append(('start_date', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


def transform_into_loan(clcs):
    """Transform the given requests into loans.

    The items current_status will be set to 'on_loan'.
    :raise: ValidationExceptions
    """
    try:
        try_transform_into_loan(clcs)
    except ValidationExceptions as e:
        raise e

    event = models.CirculationLoanCycle.EVENT_TRANSFORMED_REQUEST

    for clc in clcs:
        clc.current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc.save()
        create_event(loan_cycle_id=clc.id, event=event)


schema = {}
