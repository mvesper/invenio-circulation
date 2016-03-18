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


def _create_indices(app):
    from elasticsearch import Elasticsearch
    from invenio_circulation.models import entities

    for name, _, cls in filter(lambda x: x[0] != 'Record', entities):
        index = cls.__tablename__
        cls._es.indices.delete(index=index, ignore=404)
        cls._es.indices.create(index=index, body=cls._mappings)

    es = Elasticsearch()
    es.indices.delete(index=app.config['INDEXER_DEFAULT_INDEX'], ignore=404)


def _create_records():
    import json
    import uuid

    from invenio_db import db
    from invenio_records.api import Record
    from invenio_indexer.api import RecordIndexer

    indexer = RecordIndexer()

    source = '/Users/maves/Work/tmp/invenio3/demo_record_json_data.json'
    with open(source, 'r') as f:
        data = json.loads(f.read())

    res = []
    for d in data:
        rec_uuid = str(uuid.uuid4())
        res.append(rec_uuid)
        r = Record.create(d, id_=rec_uuid)
        indexer.index(r)

    db.session.commit()

    return res


def _clean_db():
    from invenio_db import db

    db.drop_all()
    db.create_all()


def _create_test_data(rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    cl = api.location.create('CCL', 'CERN CENTRAL LIBRARY', '')
    clr = api.loan_rule.create('default', 'period', 28, True, True, True, True)
    clrm = api.loan_rule_match.create(clr.id, '*', '*', '*', True)
    cu = api.user.create(1, 934657, 'John Doe', '3 1-014', 'C27800',
                         'john.doe@cern.ch', '+41227141337', '',
                         models.CirculationUser.GROUP_DEFAULT)
    ci = api.item.create(rec_uuids[0], cl.id, '978-1934356982', 'CM-B00001338',
                         'books', '13.37', 'Vol 1', 'no desc',
                         models.CirculationItem.STATUS_ON_SHELF,
                         models.CirculationItem.GROUP_BOOK)

    return cl, clr, clrm, cu, ci


def _delete_test_data(*args):
    for arg in args:
        arg.delete()


def _create_dates(start_days=0, start_weeks=0, end_days=0, end_weeks=4):
    import datetime

    start_date = (datetime.date.today() +
                  datetime.timedelta(days=start_days, weeks=start_weeks))
    end_date = (start_date +
                datetime.timedelta(days=end_days, weeks=end_weeks))
    return start_date, end_date


def _setup(app):
    from flask_cli import FlaskCLI
    from invenio_db import InvenioDB
    from invenio_indexer import InvenioIndexer
    from invenio_search import InvenioSearch

    FlaskCLI(app)
    InvenioDB(app)
    InvenioIndexer(app)
    InvenioSearch(app)
    InvenioCirculation(app)

    db_uri = 'postgresql+psycopg2://invenio3:dbpass123@localhost:5432/invenio3'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri


@pytest.fixture(scope='module')
def state():
    return {'app': None, 'rec_uuids': None}


@pytest.fixture
def rec_uuids(state, current_app):
    if not state['rec_uuids']:
        with current_app.app_context():
            state['rec_uuids'] = _create_records()

    return state['rec_uuids']


@pytest.fixture
def current_app(state, app):
    if not state['app']:
        _setup(app)
        with app.app_context():
            _clean_db()
            _create_indices(app)
        state['app'] = app

    return state['app']


def test_loan_cycle_create(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        query = 'loan_cycle_id:{0} event:{1}'.format(
                ci.id, models.CirculationLoanCycle.EVENT_CREATE)
        assert len(models.CirculationEvent.search(query)) == 1

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_update(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        assert clc.delivery is None
        api.loan_cycle.update(clc, delivery='foo')
        assert clc.delivery == 'foo'
        assert models.CirculationLoanCycle.get(clc.id).delivery == 'foo'

        query = 'loan_cycle_id:{0} event:{1}'.format(
                ci.id, models.CirculationLoanCycle.EVENT_CHANGE)
        assert len(models.CirculationEvent.search(query)) == 1

        # Change to the same value, shouldn't update anything,
        # nor create an event
        api.loan_cycle.update(clc, delivery='foo')
        assert len(models.CirculationEvent.search(query)) == 1

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_delete(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        id = clc.id
        api.loan_cycle.delete(clc)

        try:
            models.CirculationLoanCycle.get(id)
            raise AssertionError('The item should not exist.')
        except Exception:
            pass

        assert models.CirculationLoanCycle.search('id:{0}'.format(id)) == []

        query = 'loan_cycle_id:{0} event:{1}'.format(
                ci.id, models.CirculationLoanCycle.EVENT_DELETE)
        assert len(models.CirculationEvent.search(query)) == 1

        _delete_test_data(cl, clr, clrm, cu, clc)


def test_loan_cycle_cancel(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        current_status = models.CirculationLoanCycle.STATUS_REQUESTED
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        api.loan_cycle.cancel_clcs([clc])

        stat = models.CirculationLoanCycle.STATUS_CANCELED
        assert models.CirculationLoanCycle.get(clc.id).current_status == stat

        query = 'loan_cycle_id:{0} event:{1}'.format(
                ci.id, models.CirculationLoanCycle.EVENT_CANCELED)
        assert len(models.CirculationEvent.search(query)) == 1

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_cancel_failure(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        current_status = models.CirculationLoanCycle.STATUS_FINISHED
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        try:
            api.loan_cycle.cancel_clcs([clc])
        except Exception as e:
            assert type(e) == ValidationExceptions

        stat = models.CirculationLoanCycle.STATUS_FINISHED
        assert models.CirculationLoanCycle.get(clc.id).current_status == stat

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_overdue(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates(start_weeks=-5)

        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        api.loan_cycle.overdue_clcs([clc])

        clc = models.CirculationLoanCycle.get(clc.id)
        stat1 = models.CirculationLoanCycle.STATUS_ON_LOAN
        stat2 = models.CirculationLoanCycle.STATUS_OVERDUE
        assert clc.current_status == stat1
        assert stat2 in clc.additional_statuses

        query = 'loan_cycle_id:{0} event:{1}'.format(
                ci.id, models.CirculationLoanCycle.EVENT_OVERDUE)
        assert len(models.CirculationEvent.search(query)) == 1

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_overdue_failure(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    import invenio_circulation.models as models
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates()

        # The LoanCycle is in the wrong status
        current_status = models.CirculationLoanCycle.STATUS_FINISHED
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        try:
            api.loan_cycle.overdue_clcs([clc])
            raise AssertionError('Overdue should not work with a LC on shelf.')
        except Exception as e:
            assert type(e) == ValidationExceptions

        # The end date is fine
        clc.current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        try:
            api.loan_cycle.overdue_clcs([clc])
            msg = 'Overdue should not work with a valid end date.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        # The LoanCycle is already overdue
        clc.end_date = datetime.date.today() - datetime.timedelta(days=1)
        stat = models.CirculationLoanCycle.STATUS_OVERDUE
        clc.additional_statuses.append(stat)
        try:
            api.loan_cycle.overdue_clcs([clc])
            msg = 'Overdue should not work when the LC is already overdue.'
            raise AssertionError(msg)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_extension(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date, end_date = _create_dates(end_weeks=2)
        requested_end_date = end_date + datetime.timedelta(weeks=1)

        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc = api.loan_cycle.create(item_id=ci.id, user_id=cu.id,
                                    current_status=current_status,
                                    start_date=start_date,
                                    end_date=end_date,
                                    desired_start_date=start_date,
                                    desired_end_date=end_date,
                                    issued_date=start_date,
                                    delivery=None)

        api.loan_cycle.loan_extension([clc], requested_end_date)

        assert clc.end_date == requested_end_date

        query = 'loan_cycle_id:{0} event:{1}'.format(
                ci.id, models.CirculationLoanCycle.EVENT_LOAN_EXTENSION)
        assert len(models.CirculationEvent.search(query)) == 1

        _delete_test_data(cl, clr, clrm, cu, ci, clc)


def test_loan_cycle_extension_failure_date_taken(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates(end_weeks=1)
        start_date2, end_date2 = _create_dates(start_weeks=2)
        requested_end_date = end_date1 + datetime.timedelta(weeks=2)

        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1)[0]
        clc_r = api.circulation.request_items(cu, [ci],
                                              start_date2, end_date2)[0]

        try:
            api.loan_cycle.loan_extension([clc_l], requested_end_date)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l, clc_r)


def test_loan_cycle_extension_failure_date_duration(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates(end_weeks=1)
        requested_end_date = end_date1 + datetime.timedelta(weeks=4)

        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1)[0]

        try:
            api.loan_cycle.loan_extension([clc_l], requested_end_date)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l)


def test_loan_cycle_extension_failure_not_renewable(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates(end_weeks=1)
        requested_end_date = end_date1 + datetime.timedelta(weeks=1)

        clr.renewable = False
        clr.save()

        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1)[0]

        try:
            api.loan_cycle.loan_extension([clc_l], requested_end_date)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l)


def test_loan_cycle_extension_failure_different_users(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        cl1, clr1, clrm1, cu1, ci1 = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates(end_weeks=1)
        requested_end_date = end_date1 + datetime.timedelta(weeks=1)

        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1)[0]
        clc_l1 = api.circulation.loan_items(cu1, [ci1],
                                            start_date1, end_date1)[0]

        try:
            api.loan_cycle.loan_extension([clc_l, clc_l1], requested_end_date)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l)
        _delete_test_data(cl1, clr1, clrm1, cu1, ci1, clc_l1)


def test_loan_cycle_extension_failure_item_status(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api
    import invenio_circulation.models as models
    from invenio_circulation.api.utils import ValidationExceptions

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates(end_weeks=1)
        requested_end_date = end_date1 + datetime.timedelta(weeks=1)

        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1)[0]
        clc_l.current_status = models.CirculationLoanCycle.STATUS_FINISHED
        clc_l.save()

        try:
            api.loan_cycle.loan_extension([clc_l], requested_end_date)
        except Exception as e:
            assert type(e) == ValidationExceptions

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l)


def test_update_waitlist_end_date(current_app, rec_uuids):
    '''
    A request in the future will be canceled, thus the end_date will be
    adjusted. Here, end_date will be set to desired_end_date.
    '''
    import invenio_circulation.api as api

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates()
        start_date2, end_date2 = _create_dates(start_weeks=2)

        clc_r = api.circulation.request_items(cu, [ci],
                                              start_date2, end_date2)[0]
        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1,
                                           waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc_r])

        assert clc_l.end_date == clc_l.desired_end_date

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l)


def test_update_waitlist_end_date1(current_app, rec_uuids):
    '''
    A request in the future will be canceled, thus the end_date will be
    adjusted. Here, end_date will be set to desired_end_date, but it lies
    before the potential end date.
    '''
    import invenio_circulation.api as api

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1, end_date1 = _create_dates(end_weeks=3)
        start_date2, end_date2 = _create_dates(start_weeks=2)

        clc_r = api.circulation.request_items(cu, [ci],
                                              start_date2, end_date2)[0]
        clc_l = api.circulation.loan_items(cu, [ci],
                                           start_date1, end_date1,
                                           waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc_r])

        assert clc_l.end_date == clc_l.desired_end_date

        _delete_test_data(cl, clr, clrm, cu, ci, clc_l)


def test_update_waitlist1(current_app, rec_uuids):
    import datetime
    import invenio_circulation.api as api

    with current_app.app_context():
        # Starts before, ends before
        # present:          |-----|
        # requested: |----|
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=5)
        end_date1 = start_date1 + datetime.timedelta(weeks=4)
        start_date2 = datetime.date.today()
        end_date2 = start_date2 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2

        # Starts before, ends in
        # present:          |-----|
        # requested:  |----|???
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=4)
        start_date2 = datetime.date.today()
        end_date2 = start_date2 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2

        # Starts before, ends after
        # present:          |-----|
        # requested:  |----|?????????
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=1)
        start_date2 = datetime.date.today()
        end_date2 = start_date2 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2

        # Starts before, ends in another
        # present:          |-----||----|
        # requested:  |----|?????????
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=1)
        start_date2 = end_date1 + datetime.timedelta(days=1)
        end_date2 = start_date2 + datetime.timedelta(weeks=4)
        start_date3 = datetime.date.today()
        end_date3 = start_date3 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2)[0]
        clc3 = api.circulation.request_items(cu, [ci],
                                             start_date3, end_date3,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2
        assert clc3.start_date == clc3.desired_start_date == start_date3
        assert clc3.end_date == clc2.start_date - datetime.timedelta(days=1)
        assert clc3.desired_end_date == end_date3

        # Starts before, ends after another
        # present:          |-----||----|
        # requested:  |----|??????????????
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=1)
        start_date2 = end_date1 + datetime.timedelta(days=1)
        end_date2 = start_date2 + datetime.timedelta(weeks=1)
        start_date3 = datetime.date.today()
        end_date3 = start_date3 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2)[0]
        clc3 = api.circulation.request_items(cu, [ci],
                                             start_date3, end_date3,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2
        assert clc3.start_date == clc3.desired_start_date == start_date3
        assert clc3.end_date == clc2.start_date - datetime.timedelta(days=1)
        assert clc3.desired_end_date == end_date3

        # Starts after, ends after
        # present:   |-----|
        # requested:         |----|
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today()
        end_date1 = start_date1 + datetime.timedelta(weeks=4)
        start_date2 = end_date1 + datetime.timedelta(days=1)
        end_date2 = start_date2 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2

        # Starts in, ends after
        # present:   |-----|
        # requested:     ???|----|
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today()
        end_date1 = start_date1 + datetime.timedelta(weeks=4)
        start_date2 = start_date1 + datetime.timedelta(weeks=1)
        end_date2 = start_date2 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2

        # Starts before, ends after
        # present:    |-----|
        # requested: ????????|----|
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=2)
        start_date2 = datetime.date.today()
        end_date2 = start_date2 + datetime.timedelta(weeks=4)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2

        # Starts in anoter, ends after
        # present:   |-2-||--1--|
        # requested:   ??????????|--3-|
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=1)
        start_date2 = datetime.date.today()
        end_date2 = start_date1 - datetime.timedelta(days=1)
        start_date3 = start_date2 + datetime.timedelta(days=1)
        end_date3 = end_date1 + datetime.timedelta(weeks=1)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2)[0]
        clc3 = api.circulation.request_items(cu, [ci],
                                             start_date3, end_date3,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2
        assert clc3.start_date == clc2.end_date + datetime.timedelta(days=1)
        assert clc3.desired_start_date == start_date3
        assert clc3.end_date == clc3.desired_end_date == end_date3

        # Starts before another, ends after
        # present:     |--2-||--1--|
        # requested:  ??????????????|--3-|
        # This cannot happen in the way the current circulation is build
        # start_date1 = datetime.date.today() + datetime.timedelta(weeks=4)
        # end_date1 = start_date1 + datetime.timedelta(weeks=4)
        # start_date2 = datetime.date.today() + datetime.timedelta(weeks=1)
        # end_date2 = start_date1 - datetime.timedelta(days=1)
        # start_date3 = end_date1 + datetime.timedelta(days=1)
        # end_date3 = start_date3 + datetime.timedelta(weeks=4)
        # desired_start_date3 = datetime.date.today()

        # clc1 = api.circulation.request_items(cu, [ci],
        #                                      start_date1, end_date1)[0]
        # clc2 = api.circulation.request_items(cu, [ci],
        #                                      start_date2, end_date2)[0]
        # clc3 = api.circulation.request_items(cu, [ci],
        #                                      start_date3, end_date3,
        #                                      waitlist=True)[0]

        # api.loan_cycle.cancel_clcs([clc1])
        # assert clc1.start_date == clc1.desired_start_date == start_date1
        # assert clc1.end_date == clc1.desired_end_date == end_date1
        # assert clc2.start_date == clc2.desired_start_date == start_date2
        # assert clc2.end_date == clc2.desired_end_date == end_date2
        # assert clc3.desired_start_date == desired_start_date3
        # assert clc3.end_date == clc3.desired_end_date == end_date3

        # Starts in, ends after
        # Starts before, ends in
        # no overlap between the request
        # present:        |--1--|
        # requested:         ????|-2-|
        # requested: |-3-|???
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=4)
        start_date2 = end_date1 - datetime.timedelta(days=1)
        end_date2 = start_date2 + datetime.timedelta(weeks=1)
        start_date3 = datetime.date.today()
        end_date3 = start_date1 + datetime.timedelta(days=1)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2,
                                             waitlist=True)[0]
        clc3 = api.circulation.request_items(cu, [ci],
                                             start_date3, end_date3,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2
        assert clc3.start_date == clc3.desired_start_date == start_date3
        assert clc3.end_date == clc3.desired_end_date == end_date3

        # Starts in, ends after
        # Starts before, ends in
        # overlap between the request
        # present:        |--1--|
        # requested:         ????|-2-|
        # requested: |-3-|????
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)
        start_date1 = datetime.date.today() + datetime.timedelta(weeks=1)
        end_date1 = start_date1 + datetime.timedelta(weeks=1)
        start_date2 = end_date1 - datetime.timedelta(days=4)
        end_date2 = start_date2 + datetime.timedelta(weeks=1)
        start_date3 = datetime.date.today()
        end_date3 = start_date2 + datetime.timedelta(days=1)

        clc1 = api.circulation.request_items(cu, [ci],
                                             start_date1, end_date1)[0]
        clc2 = api.circulation.request_items(cu, [ci],
                                             start_date2, end_date2,
                                             waitlist=True)[0]
        clc3 = api.circulation.request_items(cu, [ci],
                                             start_date3, end_date3,
                                             waitlist=True)[0]

        api.loan_cycle.cancel_clcs([clc1])
        assert clc1.start_date == clc1.desired_start_date == start_date1
        assert clc1.end_date == clc1.desired_end_date == end_date1
        assert clc2.start_date == clc2.desired_start_date == start_date2
        assert clc2.end_date == clc2.desired_end_date == end_date2
        assert clc3.start_date == clc3.desired_start_date == start_date3
        assert clc3.end_date == clc2.start_date - datetime.timedelta(days=1)
        assert clc3.desired_end_date == end_date3
