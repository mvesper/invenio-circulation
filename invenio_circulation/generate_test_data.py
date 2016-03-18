def create_indices(app):
    from invenio_circulation.models import entities

    for name, _, cls in filter(lambda x: x[0] != 'Record', entities):
        index = cls.__tablename__
        cls._es.indices.delete(index=index, ignore=404)
        cls._es.indices.create(index=index, body=cls._mappings)

    from elasticsearch import Elasticsearch

    es = Elasticsearch()
    es.indices.delete(index=app.config['INDEXER_DEFAULT_INDEX'], ignore=404)


def create_records():
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
        d['uuid'] = rec_uuid
        r = Record.create(d, id_=rec_uuid)
        indexer.index(r)

    # TODO: don't know if this one is needed
    # db.session.commit()

    return res


def generate(app=None):
    import datetime
    import invenio_circulation.models as models
    import invenio_circulation.api as api

    create_indices(app)
    rec_uuids = create_records()

    rid = rec_uuids[0]

    location1 = api.location.create('ccl', 'CERN central library', '')

    item1 = api.item.create(rid, 1, 'isbn1', 'barcode1', 'books', 'shelf1',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)
    item2 = api.item.create(rid, 1, 'isbn2', 'barcode2', 'books', 'shelf2',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)
    item3 = api.item.create(rid, 1, 'isbn3', 'barcode3', 'books', 'shelf3',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)
    item4 = api.item.create(rid, 1, 'isbn4', 'barcode4', 'books', 'shelf4',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)
    item5 = api.item.create(rid, 1, 'isbn5', 'barcode5', 'books', 'shelf5',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)
    item6 = api.item.create(rid, 1, 'isbn6', 'barcode6', 'books', 'shelf6',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)
    item7 = api.item.create(rid, 1, 'isbn7', 'barcode7', 'books', 'shelf7',
                            'vol1', '', 'on_shelf',
                            models.CirculationItem.GROUP_BOOK)

    user = api.user.create(None, 'ccid1', 'John Doe', 'Random Street',
                           'Mailbox', 'john.doe@mail.com', 'phone1', '',
                           models.CirculationUser.GROUP_DEFAULT)

    header = 'Dear Mr/Mrs/Ms {{name}}'
    content = ('\nYou successfully {{action}} the following item(s)\n'
               '{% for item in items %}'
               '\t{{item}}\n'
               '{% endfor %}')
    mt1 = api.mail_template.create('item_loan', 'Loan confirmation', header,
                                   content)
    mt2 = api.mail_template.create('overdue_letter_1', 'Overdue Letter 1',
                                   header, content)
    mt3 = api.mail_template.create('overdue_letter_2', 'Overdue Letter 2',
                                   header, content)

    lr1 = api.loan_rule.create('default', 'period', 28, True, True, True, True)
    lrm1 = api.loan_rule_match.create(lr1.id, '*', '*', '*', True)

    # latest loaned item
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(weeks=4)

    api.circulation.loan_items(user, [item1], start_date, end_date)

    # Overdue item
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(weeks=4)
    start_date1 = datetime.date.today() - datetime.timedelta(weeks=5)
    end_date1 = start_date1 + datetime.timedelta(weeks=4)

    clc = api.circulation.loan_items(user, [item2], start_date, end_date)[0]
    clc.start_date = start_date1
    clc.end_date = end_date1
    clc.additional_statuses.append(models.CirculationLoanCycle.STATUS_OVERDUE)
    clc.save()

    # items on shelf pending request
    start_date = datetime.date.today() + datetime.timedelta(weeks=2)
    end_date = start_date + datetime.timedelta(weeks=4)

    api.circulation.request_items(user, [item3], start_date, end_date)

    # items on loan with pending request
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(weeks=4)
    api.circulation.loan_items(user, [item4], start_date, end_date)

    start_date = datetime.date.today() + datetime.timedelta(weeks=6)
    end_date = start_date + datetime.timedelta(weeks=4)
    api.circulation.request_items(user, [item4], start_date, end_date)

    # Overdue item with pending request
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(weeks=4)

    clc = api.circulation.loan_items(user, [item5], start_date, end_date)[0]
    clc.start_date = start_date1
    clc.end_date = end_date1
    clc.additional_statuses.append(models.CirculationLoanCycle.STATUS_OVERDUE)
    clc.save()

    start_date = datetime.date.today() + datetime.timedelta(weeks=2)
    end_date = start_date + datetime.timedelta(weeks=4)
    api.circulation.request_items(user, [item5], start_date, end_date)

    # Item with shorter loan_period
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(weeks=2)

    clc = api.circulation.loan_items(user, [item7], start_date, end_date)[0]


def grant_access_rights(user):
    from invenio_db import db
    from invenio_access.models import ActionUsers
    from invenio_circulation.acl import circulation_admin_action

    db.session.add(ActionUsers.allow(circulation_admin_action, user=user))
    db.session.commit()
