# coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2011, 2012, 2013 CERN.
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

"""
bibcirculation database models.
"""

from sqlalchemy import ForeignKey, func
from invenio_db import db
from sqlalchemy_utils import Timestamp

import datetime
import jsonpickle
import json
import importlib
import elasticsearch

# from invenio_records.api import RecordMetadata
# from invenio_records.models import Record
# from invenio_records.api import get_record
# from invenio.ext.sqlalchemy import db
from sqlalchemy.ext import mutable
from sqlalchemy.orm import subqueryload_all


class CirculationPickleHandler(jsonpickle.handlers.BaseHandler):
    def _get_class(self, string):
        module_name, class_name = string.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return module.__getattribute__(class_name)

    def flatten(self, obj, data):
        data['id'] = obj.id
        return data

    def restore(self, obj):
        cls = self._get_class(obj['py/object'])
        return cls.get(obj['id'])


class ArrayType(db.TypeDecorator):
    impl = db.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value == 'null':
            return []
        return json.loads(value)

    def copy(self):
        return ArrayType(self.impl.length)


class CirculationObject(object):
    _es = elasticsearch.Elasticsearch()

    def __str__(self):
        try:
            return "{0}('{1}')".format(self.__class__.__name__, self.id)
        except AttributeError:
            return "{0}()".format(self.__class__.__name__)

    def __repr__(self):
        try:
            return "{0}('{1}')".format(self.__class__.__name__, self.id)
        except AttributeError:
            return "{0}()".format(self.__class__.__name__)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    @classmethod
    def new(cls, **kwargs):
        kwargs['creation_date'] = datetime.datetime.now()
        kwargs['modification_date'] = datetime.datetime.now()
        obj = cls(**kwargs)
        obj.save()

        return obj

    @classmethod
    def get_all(cls):
        return [cls.get(x.id) for x in cls.query.all()]

    @classmethod
    def get(cls, id):
        obj = cls.query.options(subqueryload_all('*')).get(id)
        if obj is None:
            msg = "A {0} object with id {1} doesn't exist"
            raise Exception(msg.format(cls.__name__, id))
        data = jsonpickle.decode(obj._data)

        if hasattr(cls, '_construction_schema'):
            for key, func in cls._construction_schema.items():
                try:
                    obj.__setattr__(key, func(data))
                except AttributeError:
                    pass

        # Getting data for other modules
        from invenio_circulation.views.utils import (
                send_signal, flatten)
        from invenio_circulation.signals import get_entity

        construction_data = flatten(send_signal(get_entity,
                                                cls.__name__, None))
        if construction_data:
            for key in construction_data:
                try:
                    obj.__setattr__(key, data[key])
                except KeyError:
                    pass

        return obj

    @classmethod
    def delete_all(cls):
        for x in cls.query.all():
            cls.get(x.id).delete()

    def delete(self):
        try:
            db.session.delete(self)
            self._es.delete(index=self.__tablename__,
                            doc_type=self.__tablename__,
                            id=self.id,
                            refresh=True)
            db.session.commit()
        except Exception:
            db.session.rollback()

    @classmethod
    def search(cls, query):
        from invenio_search.api import Query
        res = cls._es.search(index=cls.__tablename__, body=Query(query).body)
        return [cls.get(x['_id']) for x in res['hits']['hits']]

    def save(self):
        try:
            """Save object to persistent storage."""
            # Dirty shit :(
            '''
            The ArrayType attribute is not tracked by SQLAlchemy, which means
            that calling save will never actually write it to the DB. Marking
            it as *dirty* does the trick.
            '''
            try:
                from sqlalchemy.orm.attributes import flag_modified
                self.additional_statuses
                flag_modified(self, 'additional_statuses')
            except (AttributeError, KeyError):
                pass
            # End of dirty shit :(

            self.modification_date = datetime.datetime.now()

            # Create dict for additional vars in _data
            db_data = {}
            if hasattr(self, '_construction_schema'):
                for key, _ in self._construction_schema.items():
                    db_data[key] = getattr(self, key)

            # Saving data for other modules
            from invenio_circulation.views.utils import (
                    send_signal, flatten)
            from invenio_circulation.signals import save_entity

            construction_data = flatten(send_signal(save_entity,
                                                    self.__class__.__name__,
                                                    None))

            if construction_data:
                for key in construction_data:
                    try:
                        db_data[key] = getattr(self, key)
                    except AttributeError:
                        pass
            # End

            self._data = jsonpickle.encode(db_data)
            db.session.add(self)
            if not hasattr(self, 'id') or self.id is None:
                db.session.flush()

            # Create dict for elasticsearch
            es_data = {}
            for key, value in self.__dict__.items():
                if key not in ['_data', '_sa_instance_state']:
                    es_data[key] = self._encode(value)

            es_data['id'] = self.id
            self._es.index(index=self.__tablename__,
                           doc_type=self.__tablename__,
                           id=self.id,
                           body=es_data,
                           refresh=True)

            db.session.commit()
        except Exception:
            db.session.rollback()

    @classmethod
    def _encode(cls, value):
        if isinstance(value, dict):
            return {key: cls._encode(val) for key, val in value.items()}
        elif isinstance(value, list):
            return [cls._encode(val) for val in value]
        elif isinstance(value, tuple):
            return [cls._encode(val) for val in value]
        elif isinstance(value, CirculationObject):
            # NEW
            return {key: cls._encode(val) for key, val
                    in value.__dict__.items()
                    if key not in ['_data', '_sa_instance_state']}
            # OLDreturn value.id
        else:
            return value

    def jsonify(self):
        def _jsonify(value):
            if isinstance(value, dict):
                res = {}
                for key, val in value.items():
                    res[key] = _jsonify(val)
                return res
            elif isinstance(value, (list, tuple)):
                return [_jsonify(val) for val in value]
            else:
                try:
                    return value.jsonify()
                except AttributeError:
                    return value

        res = {}
        for key, value in self.__dict__.items():
            if key == '_sa_instance_state':
                continue
            res[key] = _jsonify(value)
        return res

    def pickle(self):
        return jsonpickle.encode(self)


def _get_authors(rec):
    res = []
    try:
        res.append(rec['main_entry_personal_name']['personal_name'])
    except KeyError:
        pass
    try:
        for author in rec['added_entry_personal_name']:
            res.append(rec['personal_name'])
    except KeyError:
        pass
    return res


class CirculationRecord(CirculationObject):
    _json_schema = {'type': 'object',
                    'title': 'Record',
                    'properties': {
                        'id': {'type': 'integer'},
                        'title': {'type': 'string'},
                        'abstract': {'type': 'string', 'format': 'textarea'},
                        'authors': {
                            'type': 'array',
                            'format': 'table',
                            'items': {
                                'type': 'string',
                                'title': 'Authors',
                                }
                            }
                        }
                    }

    _construction_schema = {
            # 'id': lambda x: x['control_number'],
            'title': lambda x: x['title_statement']['title'],
            'abstract': lambda x: x['summary'][0]['expansion_of_summary_note'],
            'authors': _get_authors}

    @classmethod
    def new(cls, **kwargs):
        raise Exception('CirculationRecord is a Wrapper class for Record.')

    @classmethod
    def get_all(cls):
        return cls.search('')

    @classmethod
    def get(cls, id):
        from invenio_records.api import Record
        json = Record.get_record(id)
        if json is None:
            raise Exception("A record with id {0} doesn't exist".format(id))
        # json['id'] = id

        obj = CirculationRecord()
        obj.id = json.id
        for key, func in cls._construction_schema.items():
            try:
                obj.__setattr__(key, func(json))
            except Exception:
                pass

        return obj

    @classmethod
    def delete_all(cls):
        raise Exception('CirculationRecord is a Wrapper class for Record.')

    def delete(self):
        raise Exception('CirculationRecord is a Wrapper class for Record.')

    @classmethod
    def search(cls, query):
        from flask import current_app as app
        from invenio_search import Query, current_search_client

        index = app.config['INDEXER_DEFAULT_INDEX']
        res = current_search_client.search(index=index,
                                           body=Query(query).body,
                                           size=1000)

        return [cls.get(x['_id']) for x in res['hits']['hits']]

    def save(self):
        raise Exception('CirculationRecord is a Wrapper class for Record.')


class CirculationItem(CirculationObject, db.Model):
    __tablename__ = 'circulation_item'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    record_id = db.Column(db.String(255))
    location_id = db.Column(db.BigInteger,
                            db.ForeignKey('circulation_location.id'))
    location = db.relationship('CirculationLocation')
    isbn = db.Column(db.String(255))
    barcode = db.Column(db.String(255))
    collection = db.Column(db.String(255))
    description = db.Column(db.String(255))
    current_status = db.Column(db.String(255))
    additional_statuses = db.Column(ArrayType(255))
    item_group = db.Column(db.String(255))
    shelf_number = db.Column(db.String(255))
    volume = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    GROUP_BOOK = 'book'

    STATUS_ON_SHELF = 'on_shelf'
    STATUS_ON_LOAN = 'on_loan'
    STATUS_IN_PROCESS = 'in_process'
    STATUS_MISSING = 'missing'

    _json_schema = {'type': 'object',
                    'title': 'Item',
                    'properties': {
                        'id': {'type': 'integer'},
                        'record_id': {'type': 'string'},
                        'location_id': {'type': 'integer'},
                        'isbn': {'type': 'string'},
                        'barcode': {'type': 'string'},
                        'collection': {'type': 'string'},
                        'shelf_number': {'type': 'string'},
                        'description': {'type': 'string'},
                        'item_group': {'type': 'string'},
                        'current_status': {'type': 'string'},
                        'volume': {'type': 'string'},
                        }
                    }

    @db.reconstructor
    def init_on_load(self):
        self.record = CirculationRecord.get(self.record_id)


class CirculationLoanCycle(CirculationObject, db.Model):
    __tablename__ = 'circulation_loan_cycle'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    current_status = db.Column(db.String(255))
    additional_statuses = db.Column(ArrayType(255))
    item_id = db.Column(db.BigInteger, db.ForeignKey('circulation_item.id'))
    item = db.relationship('CirculationItem')
    user_id = db.Column(db.BigInteger, db.ForeignKey('circulation_user.id'))
    user = db.relationship('CirculationUser')
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    desired_start_date = db.Column(db.Date)
    desired_end_date = db.Column(db.Date)
    delivery = db.Column(db.String(255))
    issued_date = db.Column(db.DateTime)
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    STATUS_ON_LOAN = 'on_loan'
    STATUS_REQUESTED = 'requested'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELED = 'canceled'
    STATUS_OVERDUE = 'overdue'

    DELIVERY_DEFAULT = 'Pick up'

    _json_schema = {'type': 'object',
                    'title': 'Loan Cycle',
                    'properties': {
                        'id': {'type': 'integer'},
                        'item_id': {'type': 'integer'},
                        'user_id': {'type': 'integer'},
                        'group_uuid': {'type': 'string'},
                        'current_status': {'type': 'string'},
                        'start_date': {'type': 'string'},
                        'end_date': {'type': 'string'},
                        'desired_start_date': {'type': 'string'},
                        'desired_end_date': {'type': 'string'},
                        'issued_date': {'type': 'string'},
                        'requested_extension_end_date': {'type': 'string'},
                        }
                    }


class CirculationUser(CirculationObject, db.Model):
    __tablename__ = 'circulation_user'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    invenio_user_id = db.Column(db.BigInteger)
    current_status = db.Column(db.String(255))
    ccid = db.Column(db.String(255))
    name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    mailbox = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(255))
    notes = db.Column(db.String(255))
    user_group = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    GROUP_DEFAULT = 'default'

    _json_schema = {'type': 'object',
                    'title': 'User',
                    'properties': {
                        'id': {'type': 'integer'},
                        'invenio_user_id': {'type': 'integer'},
                        'ccid': {'type': 'string'},
                        'name': {'type': 'string'},
                        'address': {'type': 'string'},
                        'mailbox': {'type': 'string'},
                        'email': {'type': 'string'},
                        'phone': {'type': 'string'},
                        'notes': {'type': 'string'},
                        'user_group': {'type': 'string'}
                        }
                    }


class CirculationLocation(CirculationObject, db.Model):
    __tablename__ = 'circulation_location'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    code = db.Column(db.String(255))
    name = db.Column(db.String(255))
    notes = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    _json_schema = {'type': 'object',
                    'title': 'Location',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'code': {'type': 'string'},
                        'notes': {'type': 'string',
                                  'format': 'textarea',
                                  'options': {'expand_height': True}},
                        }
                    }


class CirculationMailTemplate(CirculationObject, db.Model):
    __tablename__ = 'circulation_mail_template'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    template_name = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    header = db.Column(db.String(255))
    content = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    _json_schema = {'type': 'object',
                    'title': 'Mail Template',
                    'properties': {
                        'id': {'type': 'integer'},
                        'template_name': {'type': 'string'},
                        'subject': {'type': 'string'},
                        'header': {'type': 'string'},
                        'content': {'type': 'string',
                                    'format': 'textarea',
                                    'options': {'expand_height': True}},
                        }
                    }


class CirculationLoanRule(CirculationObject, db.Model):
    __tablename__ = 'circulation_loan_rule'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    name = db.Column(db.String(255))
    type = db.Column(db.String(255))
    loan_period = db.Column(db.Integer)
    holdable = db.Column(db.Boolean)
    home_pickup= db.Column(db.Boolean)
    renewable = db.Column(db.Boolean)
    automatic_recall = db.Column(db.Boolean)
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    _json_schema = {'type': 'object',
                    'title': 'Loan Rule',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'type': {'type': 'string'},
                        'loan_period': {'type': 'integer'},
                        'holdable': {'type': 'boolean'},
                        'home_pickup': {'type': 'boolean'},
                        'automatic_recall': {'type': 'boolean'},
                        }
                    }


class CirculationLoanRuleMatch(CirculationObject, db.Model):
    __tablename__ = 'circulation_loan_rule_match'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    loan_rule_id = db.Column(db.BigInteger,
                             db.ForeignKey('circulation_loan_rule.id',
                                           ondelete="SET NULL"))
    loan_rule = db.relationship('CirculationLoanRule')
    item_type = db.Column(db.String(255))
    patron_type = db.Column(db.String(255))
    location_code = db.Column(db.String(255))
    active = db.Column(db.Boolean)
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    _json_schema = {'type': 'object',
                    'title': 'Loan Rule',
                    'properties': {
                        'id': {'type': 'integer'},
                        'loan_rule_id': {'type': 'integer'},
                        'item_type': {'type': 'string'},
                        'patron_type': {'type': 'string'},
                        'location_code': {'type': 'string'},
                        'active': {'type': 'boolean'},
                        }
                    }


class CirculationEvent(CirculationObject, db.Model):
    __tablename__ = 'circulation_event'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey('circulation_user.id',
                                                     ondelete="SET NULL"))
    user = db.relationship('CirculationUser')
    item_id = db.Column(db.BigInteger, db.ForeignKey('circulation_item.id',
                                                     ondelete="SET NULL"))
    item = db.relationship('CirculationItem')
    loan_cycle_id = db.Column(db.BigInteger,
                              db.ForeignKey('circulation_loan_cycle.id',
                                            ondelete="SET NULL"))
    loan_cycle = db.relationship('CirculationLoanCycle')
    location_id = db.Column(db.BigInteger,
                            db.ForeignKey('circulation_location.id',
                                          ondelete="SET NULL"))
    location = db.relationship('CirculationLocation')
    mail_template_id = db.Column(db.BigInteger,
                                 db.ForeignKey('circulation_mail_template.id',
                                               ondelete="SET NULL"))
    mail_template = db.relationship('CirculationMailTemplate')
    loan_rule_id = db.Column(db.BigInteger,
                             db.ForeignKey('circulation_loan_rule.id',
                                           ondelete="SET NULL"))
    loan_rule = db.relationship('CirculationLoanRule')
    loan_rule_match_id = db.Column(db.BigInteger,
            db.ForeignKey('circulation_loan_rule_match.id',
            ondelete="SET NULL"))
    loan_rule_match = db.relationship('CirculationLoanRuleMatch')
    event = db.Column(db.String(255))
    description = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    EVENT_ITEM_CREATE = 'item_created'
    EVENT_ITEM_CHANGE = 'item_changed'
    EVENT_ITEM_DELETE = 'item_deleted'
    EVENT_ITEM_MISSING = 'item_missing'
    EVENT_ITEM_RETURNED_MISSING = 'item_returned_missing'
    EVENT_ITEM_IN_PROCESS = 'item_in_process'
    EVENT_USER_CREATE = 'user_created'
    EVENT_USER_CHANGE = 'user_changed'
    EVENT_USER_DELETE = 'user_deleted'
    EVENT_CLC_CREATE = 'clc_created'
    EVENT_CLC_DELETE = 'clc_deleted'
    EVENT_CLC_CREATED_LOAN = 'clc_created_loan'
    EVENT_CLC_CREATED_REQUEST = 'clc_created_request'
    EVENT_CLC_FINISHED = 'clc_finish'
    EVENT_CLC_CANCELED = 'clc_canceled'
    EVENT_CLC_UPDATED = 'clc_updated'
    EVENT_CLC_OVERDUE = 'clc_overdue'
    EVENT_CLC_OVERDUE_LETTER = 'clc_overdue_letter'
    EVENT_CLC_REQUEST_LOAN_EXTENSION = 'clc_request_loan_extension'
    EVENT_CLC_LOAN_EXTENSION = 'clc_loan_extension'
    EVENT_LOCATION_CREATE = 'location_created'
    EVENT_LOCATION_CHANGE = 'location_changed'
    EVENT_LOCATION_DELETE = 'location_deleted'
    EVENT_MT_CREATE = 'mail_template_created'
    EVENT_MT_CHANGE = 'mail_template_changed'
    EVENT_MT_DELETE = 'mail_template_deleted'
    EVENT_LR_CREATE = 'loan_rule_created'
    EVENT_LR_CHANGE = 'loan_rule_changed'
    EVENT_LR_DELETE = 'loan_rule_deleted'
    EVENT_LRM_CREATE = 'loan_rule_match_created'
    EVENT_LRM_CHANGE = 'loan_rule_match_changed'
    EVENT_LRM_DELETE = 'loan_rule_match_deleted'

    _json_schema = {'type': 'object',
                    'title': 'Event',
                    'properties': {
                        'id': {'type': 'integer'},
                        'user_id': {'type': 'integer'},
                        'item_id': {'type': 'integer'},
                        'loan_cycle_id': {'type': 'integer'},
                        'location_id': {'type': 'integer'},
                        'loan_rule_id': {'type': 'integer'},
                        'loan_rule_match_id': {'type': 'integer'},
                        'mail_template_id': {'type': 'integer'},
                        'event': {'type': 'string'},
                        'description': {'type': 'string'},
                        'creation_date': {'type': 'string'},
                        }
                    }


jsonpickle.handlers.registry.register(CirculationRecord,
                                      CirculationPickleHandler)
jsonpickle.handlers.registry.register(CirculationItem,
                                      CirculationPickleHandler)
jsonpickle.handlers.registry.register(CirculationLoanCycle,
                                      CirculationPickleHandler)
jsonpickle.handlers.registry.register(CirculationUser,
                                      CirculationPickleHandler)
jsonpickle.handlers.registry.register(CirculationLocation,
                                      CirculationPickleHandler)
jsonpickle.handlers.registry.register(CirculationEvent,
                                      CirculationPickleHandler)
jsonpickle.handlers.registry.register(CirculationMailTemplate,
                                      CirculationPickleHandler)

# Display Name , link name, entity
entities = [('Record', 'record', CirculationRecord),
            ('User', 'user', CirculationUser),
            ('Item', 'item', CirculationItem),
            ('Loan Cycle', 'loan_cycle', CirculationLoanCycle),
            ('Location', 'location', CirculationLocation),
            ('Event', 'event', CirculationEvent),
            ('Mail Template', 'mail_template', CirculationMailTemplate),
            ('Loan Rule', 'loan_rule', CirculationLoanRule)]
