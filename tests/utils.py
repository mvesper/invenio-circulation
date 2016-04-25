import pytest


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
    from invenio_pidstore.minters import recid_minter
    from invenio_records.api import Record
    from invenio_indexer.api import RecordIndexer

    indexer = RecordIndexer()

    source = '/Users/maves/Work/tmp/invenio3/demo_record_json_data.json'
    with open(source, 'r') as f:
        data = json.loads(f.read())

    res = []
    for d in data:
        rec_uuid = uuid.uuid4()
        rec_id = int(recid_minter(rec_uuid, d).pid_value)
        d[u'recid'] = rec_id
        d[u'uuid'] = unicode(str(rec_uuid))
        res.append(rec_id)
        r = Record.create(d, id_=rec_uuid)
        indexer.index(r)

    db.session.commit()

    return res


def _clean_db():
    import invenio_circulation.models as models
    '''
    db.drop_all()
    db.create_all()
    '''
    models.CirculationUser.delete_all()
    models.CirculationLoanCycle.delete_all()
    models.CirculationLocation.delete_all()
    models.CirculationLoanRule.delete_all()
    models.CirculationLoanRuleMatch.delete_all()
    models.CirculationEvent.delete_all()
    models.CirculationMailTemplate.delete_all()
    models.CirculationItem.delete_all()


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
    from invenio_circulation import InvenioCirculation

    FlaskCLI(app)
    InvenioDB(app)
    InvenioIndexer(app)
    InvenioSearch(app)
    InvenioCirculation(app)

    db_uri = 'postgresql+psycopg2://localhost/cds'
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
