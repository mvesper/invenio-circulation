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

"""invenio-circulation api responsible for CirculationItem handling."""

import invenio_circulation.models as models
from invenio_circulation.api.checks import check_item_statuses
from invenio_circulation.api.loan_cycle import cancel_clcs, overdue_clcs
from invenio_circulation.api.utils import ValidationExceptions, run_checks
from invenio_circulation.signals import (circulation_item_created,
                                         circulation_item_deleted,
                                         circulation_item_lost,
                                         circulation_item_missing_returned,
                                         circulation_item_process_returned,
                                         circulation_item_processed,
                                         circulation_item_updated)
from invenio_circulation.transaction import persist, persistent_context


@persist
def create(record, location, isbn, barcode, shelf_number,
           description, current_status, item_group):
    """Create a CirculationItem object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    location = location.copy()
    location['classification_part'] = shelf_number
    data = {'international_standard_book_number': {
                    'international_standard_book_number': isbn},
            'item_information_general_information': {
                    'piece_designation': barcode,
                    'public_note': item_group,
                    'materials_specified': description},
            'location': location,
            'record': record,
            'local_data': {'current_status': current_status}}
    item = models.CirculationItem.create(data)

    return item


def try_lose_items(items):
    """Check the conditions to lose the given items.

    Checked conditions:
    * The current_status must be 'on_shelf', 'on_loan' or 'in_process'.

    :raise: ValidationExceptions
    """
    params = dict(items=items,
                  statuses=[models.CirculationItem.STATUS_ON_LOAN,
                            models.CirculationItem.STATUS_ON_SHELF,
                            models.CirculationItem.STATUS_IN_PROCESS])
    funcs = [('item_status', check_item_statuses)]

    run_checks(funcs, params)


def lose_items(items):
    """Lose the given items.

    This sets the current_status to missing.
    All CirculationLoanCycles with current_status 'on_loan' or 'requested'
    associated with the given item will be canceled.

    :raise: ValidationExceptions
    """
    try:
        try_lose_items(items)
    except ValidationExceptions as e:
        raise e

    CLC = models.CirculationLoanCycle

    with persistent_context():
        for item in items:
            item['local_data']['current_status'] = models.CirculationItem.STATUS_MISSING
            item.commit()

            circulation_item_lost.send(item)

            statuses = [models.CirculationLoanCycle.STATUS_REQUESTED,
                        models.CirculationLoanCycle.STATUS_ON_LOAN]
            clcs = [x for status in statuses
                    for x in CLC.mechanical_query(
                        {'item.uuid': item['uuid'], 'current_status': status})]

            cancel_clcs(clcs)


def try_return_missing_items(items):
    """Check the conditions to return the given missing items.

    Checked conditions:
    * The current_status must be 'missing'.

    :raise: ValidationExceptions
    """
    params = dict(items=items,
                  statuses=[models.CirculationItem.STATUS_MISSING])
    funcs = [('item_status', check_item_statuses)]

    run_checks(funcs, params)


def return_missing_items(items):
    """Return the missing items.

    The items current_status will be set to 'on_shelf'.
    :raise: ValidationExceptions
    """
    try:
        try_return_missing_items(items)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for item in items:
            item['local_data']['current_status'] = models.CirculationItem.STATUS_ON_SHELF
            item.commit()
            circulation_item_missing_returned.send(item)


def try_process_items(items):
    """Check the conditions to process the items.

    Checked conditions:
    * The current_status must be 'on_shelf'

    :raise: ValidationExceptions
    """
    params = dict(items=items,
                  statuses=[models.CirculationItem.STATUS_ON_SHELF])
    funcs = [('item_status', check_item_statuses)]

    run_checks(funcs, params)


def process_items(items, description):
    """Process the given items.

    The items current_status will be set to 'in_process'.

    :param description: The reason of the processing of the items.
    :raise: ValidationExceptions
    """
    try:
        try_process_items(items)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for item in items:
            item['local_data']['current_status'] = models.CirculationItem.STATUS_IN_PROCESS
            item.commit()
            circulation_item_processed.send(item)


def try_return_processed_items(items):
    """Check the conditions to return the processed items.

    Checked conditions:
    * The current_status must be 'in_process'

    :raise: ValidationExceptions
    """
    params = dict(items=items,
                  statuses=[models.CirculationItem.STATUS_IN_PROCESS])
    funcs = [('item_status', check_item_statuses)]

    run_checks(funcs, params)


def return_processed_items(items):
    """Return the given processed items.

    The items current_status will be set to 'on_shelf'.
    :raise: ValidationExceptions
    """
    try:
        try_return_processed_items(items)
    except ValidationExceptions as e:
        raise e

    with persistent_context():
        for item in items:
            item['local_data']['current_status'] = models.CirculationItem.STATUS_ON_SHELF
            item.commit()
            circulation_item_process_returned.send(item)


def overdue_items(items):
    """Overdue the given items.

    This function simply calls api.loan_cycle.overdue_clcs.
    :raise: ValidationExceptions
    """
    with persistent_context():
        status = models.CirculationLoanCycle.STATUS_ON_LOAN
        for item in items:
            query = {'local_data.item.uuid': item['uuid'], 'local_data.current_status': status}
            overdue_clcs(models.CirculationLoanCycle.mechanical_query(query))
