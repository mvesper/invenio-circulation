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


"""Pytest configuration."""

from __future__ import absolute_import, print_function, unicode_literals

import os
import shutil
import tempfile

import pytest
from flask import Flask
from flask_celeryext import FlaskCeleryExt
from flask_cli import FlaskCLI
from invenio_db import db as db_
from invenio_db import InvenioDB
from invenio_indexer import InvenioIndexer
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_mail import InvenioMail
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records_rest import InvenioRecordsREST, config
from invenio_records_rest.utils import PIDConverter
from invenio_search import InvenioSearch
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_circulation import InvenioCirculation


@pytest.yield_fixture()
def app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()
    app_ = Flask(__name__, instance_path=instance_path)
    app_.config.update(
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND="cache",
        SECRET_KEY="CHANGE_ME",
        SECURITY_PASSWORD_SALT="CHANGE_ME_ALSO",
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        TESTING=True,
        SERVER_NAME=os.environ.get(
            'SERVER_NAME', 'localhost:5000'),
        RECORDS_REST_ENDPOINTS=config.RECORDS_REST_ENDPOINTS,
    )

    # INDEXER_REPLACE_REFS=False,
    app_.url_map.converters['pid'] = PIDConverter

    FlaskCLI(app_)
    FlaskCeleryExt(app_)
    InvenioDB(app_)
    InvenioRecords(app_)
    InvenioRecordsREST(app_)
    InvenioPIDStore(app_)
    InvenioMail(app_)
    InvenioCirculation(app_)
    InvenioSearch(app_)
    InvenioJSONSchemas(app_)
    InvenioIndexer(app_)

    with app_.app_context():
        yield app_

    shutil.rmtree(instance_path)


@pytest.yield_fixture()
def db(app):
    """Database fixture."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))

    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.yield_fixture()
def record(app, db):
    import uuid

    from invenio_indexer.api import RecordIndexer
    from invenio_pidstore.minters import recid_minter
    from invenio_records.api import Record

    rec = {}

    id = str(uuid.uuid4())
    pid = recid_minter(id, rec)
    rec[u'uuid'] = id
    rec[u'control_number'] = pid.pid_value
    rec[u'recid'] = pid.pid_value
    rec[u'title_statement'] = {'title': 'Test Title'}
    r = Record.create(rec, id_=id)

    db.session.commit()

    RecordIndexer().index(r)

    yield r


@pytest.yield_fixture()
def user(app, db):
    from invenio_accounts.models import User
    from invenio_userprofiles import UserProfile

    user = User(email='john.doe@mail.com', password='123456')
    up = UserProfile(username='John', full_name='John Doe')
    user.profile = up
    db.session.add(user)
    db.session.add(up)
    db.session.commit()

    yield user


@pytest.yield_fixture()
def location(app, db):
    import invenio_circulation.api as api

    loc = api.location.create(name='CERN Central', address='ccl', notes='')

    yield loc


@pytest.yield_fixture()
def item(db, app, record, location):
    import invenio_circulation.api as api
    import invenio_circulation.models as models

    item = api.item.create(record, location, 'isbn', 'barcode',
                           'shelf_number', 'description',
                           models.CirculationItem.STATUS_ON_SHELF,
                           models.CirculationItem.GROUP_BOOK)
    db.session.commit()

    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')

    yield item
