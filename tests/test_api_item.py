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


def test_item_create(db, app, record, location):
    item = api.item.create(record, location, 'isbn', 'barcode',
                           'shelf_number', 'description',
                           models.CirculationItem.STATUS_ON_SHELF,
                           models.CirculationItem.GROUP_BOOK)
    db.session.commit()

    assert item['record'] == record

    name = location['location']['sublocation_or_collection']
    address = location['location']['address']
    notes = location['location']['nonpublic_notes']

    assert item['location']['classification_part'] == 'shelf_number'
    assert item['location']['sublocation_or_collection'] == name
    assert item['location']['address'] == address
    assert item['location']['nonpublic_notes'] == notes

    assert item['international_standard_book_number'][
                'international_standard_book_number'] == 'isbn'
    assert item['item_information_general_information'][
                'piece_designation'] == 'barcode'
    assert item['item_information_general_information'][
                'public_note'] == models.CirculationItem.GROUP_BOOK
    assert item['item_information_general_information'][
                'materials_specified'] == 'description'
    assert item['local_data'][
                'current_status'] == models.CirculationItem.STATUS_ON_SHELF

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    res = models.CirculationItem.search('uuid:{0}'.format(item['uuid']))

    assert len(res) == 1
    assert res[0] == item


def test_item_update(db, app, item):
    assert item['international_standard_book_number'][
                'international_standard_book_number'] == 'isbn'
    item['international_standard_book_number'][
         'international_standard_book_number'] = 'foo'
    item.commit()
    db.session.commit()
    assert item['international_standard_book_number'][
                'international_standard_book_number'] == 'foo'

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    res = models.CirculationItem.search('uuid:{0}'.format(item['uuid']))
    assert len(res) == 1
    assert res[0]['international_standard_book_number'][
                  'international_standard_book_number'] == 'foo'


def test_item_delete(db, app, item):
    res = models.CirculationItem.search('uuid:{0}'.format(item['uuid']))
    assert len(res) == 1
    assert res[0]['uuid'] == item['uuid']

    item.delete()
    db.session.commit()

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')
    res = models.CirculationItem.search('uuid:{0}'.format(item['uuid']))
    assert len(res) == 0


def test_item_lose(db, app, item):
    api.item.lose_items([item])
    db.session.commit()

    cs = models.CirculationItem.get_record(item['uuid'])[
            'local_data']['current_status']
    assert cs == models.CirculationItem.STATUS_MISSING


def test_item_lose_failure(app, item):
    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_MISSING

    try:
        api.item.lose_items([item])
        raise AssertionError('A missing item can not be lost again.')
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_item_return_missing(db, app, item):
    api.item.lose_items([item])
    db.session.commit()

    item = models.CirculationItem.get_record(item['uuid'])
    api.item.return_missing_items([item])
    db.session.commit()

    cs = models.CirculationItem.get_record(
        item['uuid'])['local_data']['current_status']
    assert cs == models.CirculationItem.STATUS_ON_SHELF


def test_item_return_missing_failure(app, item):
    try:
        api.item.return_missing_items([item])
        msg = 'A present item can not be returned from missing.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_item_process(db, app, item):
    api.item.process_items([item], 'test')
    db.session.commit()

    cs = models.CirculationItem.get_record(
        item['uuid'])['local_data']['current_status']
    assert cs == models.CirculationItem.STATUS_IN_PROCESS


def test_item_process_failure(app, item):
    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_MISSING

    try:
        api.item.process_items([item], 'test')
        msg = 'The item must be in status on_shelf.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_item_process_return(db, app, item):
    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_IN_PROCESS

    api.item.return_processed_items([item])
    db.session.commit()

    cs = models.CirculationItem.get_record(
        item['uuid'])['local_data']['current_status']
    assert cs == models.CirculationItem.STATUS_ON_SHELF


def test_item_process_return_failure(app, item):
    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_MISSING

    try:
        api.item.return_processed_items([item])
        msg = 'The item must be in status in_process.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions


def test_item_overdue(db, app, user, item):
    start_date, end_date = _create_dates()
    clcs = api.circulation.loan_items(user, [item],
                                      start_date, end_date, False)

    clc = clcs[0]
    clc['local_data']['end_date'] = start_date - datetime.timedelta(days=1)
    clc.commit()
    db.session.commit()

    api.item.overdue_items([item])
    db.session.commit()

    clc = models.CirculationLoanCycle.get_record(clc['uuid'])

    stat = models.CirculationLoanCycle.STATUS_OVERDUE
    assert stat in clc['local_data']['additional_statuses']


def test_item_overdue_failure(db, app, user, item):
    start_date, end_date = _create_dates()
    api.circulation.loan_items(user, [item], start_date, end_date, False)
    db.session.commit()

    item['local_data'][
         'current_status'] = models.CirculationItem.STATUS_ON_SHELF

    try:
        api.item.overdue_items([item])
        msg = 'The item must be in status on_loan.'
        raise AssertionError(msg)
    except Exception as e:
        assert type(e) == ValidationExceptions
