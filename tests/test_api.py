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


def test_create(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        cl, clr, clrm, cu, ci = _create_test_data(rec_uuids)

        creates = {'loan_rule': ['default', 'period', 28,
                                 True, True, True, True],
                   'loan_rule_match': [clr.id, '*', '*', '*', True],
                   'location': ['CCL', 'CERN CENTRAL LIBRARY', ''],
                   'mail_template': ['foo', 'foo', 'foo', 'foo'],
                   'user': [1, 934657, 'John Doe', '3 1-014', 'C27800',
                            'john.doe@cern.ch', '+41227141337', '',
                            models.CirculationUser.GROUP_DEFAULT]}

        changes = {'loan_rule': 'name',
                   'loan_rule_match': 'item_type',
                   'location': 'name',
                   'mail_template': 'template_name',
                   'user': 'name'}

        objs = []
        for key, val in creates.items():
            # Test create
            _api = getattr(api, key)
            obj = _api.create(*val)
            _id = obj.id
            assert obj.get(_id)

            # Test update
            _api.update(obj, **dict([(changes[key], 'bar')]))
            assert getattr(obj.get(_id), changes[key]) == 'bar'

            # Test delete
            _api.delete(obj)
            try:
                obj.get(_id)
                raise AssertionError('The object should not be there anymore.')
            except Exception:
                pass


def test_event_create(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        ce = api.event.create()
        assert models.CirculationEvent.get(ce.id)


def test_event_update(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        ce = api.event.create()

        try:
            api.event.update(ce)
            raise AssertionError('Updating an event should not be possible.')
        except Exception as e:
            pass


def test_event_delete(current_app, rec_uuids):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    with current_app.app_context():
        ce = api.event.create()

        try:
            api.event.delete(ce)
            raise AssertionError('Deleting an event should not be possible.')
        except Exception as e:
            pass
