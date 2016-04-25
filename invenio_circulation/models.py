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

"""invenio-circulation database models."""

import datetime
import importlib
import json

import elasticsearch
import jsonpickle

from invenio_db import db
from sqlalchemy.orm import subqueryload_all


class CirculationPickleHandler(jsonpickle.handlers.BaseHandler):
    """Helper class to pickle CirculationObject objects.

    deprecated
    """

    def _get_class(self, string):
        module_name, class_name = string.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return module.__getattribute__(class_name)

    def flatten(self, obj, data):
        """Flatten a CirculationObject to a json-friendly form.

        :param obj: The CirculationObject to pickle.
        :param data: Provided to store the json form.
        """
        data['id'] = obj.id
        return data

    def restore(self, obj):
        """Restore the json-friendly obj to a CirculationObject."""
        cls = self._get_class(obj['py/object'])
        return cls.get(obj['id'])


class ArrayType(db.TypeDecorator):
    """SQLAlchemy type decorator to store an array in the database."""

    impl = db.String

    def process_bind_param(self, value, dialect):
        """Translate the given array to something storable."""
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Translate the stored value to an array."""
        if value == 'null':
            return []
        return json.loads(value)

    def copy(self):
        """Produce a copy of ArrayType."""
        return ArrayType(self.impl.length)


class CirculationObject(object):
    """Base class of invenio-circulation entities.

    Provides general database and elasticsearch functionality.
    """

    _es = elasticsearch.Elasticsearch()

    def __str__(self):
        """Get the string representation for the given object."""
        try:
            return "{0}('{1}')".format(self.__class__.__name__, self.id)
        except AttributeError:
            return "{0}()".format(self.__class__.__name__)

    def __repr__(self):
        """Get the string representation for the given object."""
        try:
            return "{0}('{1}')".format(self.__class__.__name__, self.id)
        except AttributeError:
            return "{0}()".format(self.__class__.__name__)

    def __init__(self, **kwargs):
        """Constructor.

        Stores all given Key-Value arguments;
        """
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    @classmethod
    def new(cls, **kwargs):
        """Store and index a new CirculationObject.

        :param kwargs: Key-Value arguments will be set and stored/indexed.
        :return: The created object.
        """
        kwargs['creation_date'] = datetime.datetime.now()
        kwargs['modification_date'] = datetime.datetime.now()
        obj = cls(**kwargs)
        obj.save()

        # SQLalchemy hack: after every flush(), the __dict__ property
        # disappears, touching the item gets it back
        _id = obj.id    # nopep8

        return obj

    @classmethod
    def get_all(cls):
        """Get all stored objects of the given class."""
        return [cls.get(x.id) for x in cls.query.all()]

    @classmethod
    def get(cls, id):
        """Get the CirculationObject associated with the given id."""
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
        """Delete all stored objects of the given class."""
        for x in cls.query.all():
            cls.get(x.id).delete()

    def delete(self):
        """Delete the object."""
        try:
            db.session.delete(self)
            self._es.delete(index=self.__tablename__,
                            doc_type=self.__tablename__,
                            id=self.id,
                            refresh=True)
            db.session.commit()
        except Exception as e:
            print e
            db.session.rollback()

    @classmethod
    def search(cls, query):
        """Search for objects using the invenio query syntax."""
        from invenio_search.api import Query

        # TODO: That seems slightly wrong xD
        def replace_field(query):
            if isinstance(query, dict):
                for key, value in query.items():
                    if key == 'fields':
                        if value == ['_all']:
                            try:
                                props = cls._all_field
                            except AttributeError:
                                props = ['_all']
                            query[key] = props
                    else:
                        replace_field(value)
            elif isinstance(query, list):
                for value in query:
                    replace_field(value)

        body = Query(query).body
        replace_field(body)
        res = cls._es.search(index=cls.__tablename__, body=body, size=10000)
        return [cls.get(x['_id']) for x in res['hits']['hits']]

    def save(self):
        """Store and index the object."""
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
        """Get a dictionary representation of the object."""
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

        # SQLalchemy hack: after every flush(), the __dict__ property
        # disappears, touching the item gets it back
        _id = self.id   # nopep8

        res = {}
        for key, value in self.__dict__.items():
            if key == '_sa_instance_state':
                continue
            res[key] = _jsonify(value)
        return res

    def pickle(self):
        """Pickle the object."""
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
    """invenio-circulation wrapper for invenio-records Records."""

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
            'authors': _get_authors,
            'edition': lambda x: x['edition_statement']}

    @classmethod
    def new(cls, **kwargs):
        """Currently not supposed to create new Records."""
        raise Exception('CirculationRecord is a Wrapper class for Record.')

    @classmethod
    def get_all(cls):
        """Get all CirculationRecords."""
        return cls.search('')

    @classmethod
    def get(cls, id):
        """Get a invenio-records Record wrapped as CirculationRecord."""
        from invenio_records.api import Record
        from invenio_pidstore.models import PersistentIdentifier

        _uuid = PersistentIdentifier.get('recid', id).object_uuid
        json = Record.get_record(_uuid)

        if json is None:
            raise Exception("A record with id {0} doesn't exist".format(id))
        # json['id'] = id

        obj = CirculationRecord()
        obj.id = id
        for key, func in cls._construction_schema.items():
            try:
                obj.__setattr__(key, func(json))
            except Exception:
                pass

        return obj

    @classmethod
    def delete_all(cls):
        """Currently not supposed to delete Records."""
        raise Exception('CirculationRecord is a Wrapper class for Record.')

    def delete(self):
        """Currently not supposed to delete Records."""
        raise Exception('CirculationRecord is a Wrapper class for Record.')

    @classmethod
    def search(cls, query):
        """Search for objects using the invenio query syntax."""
        from flask import current_app as app
        from invenio_search import Query, current_search_client

        index = app.config['INDEXER_DEFAULT_INDEX']
        res = current_search_client.search(index=index,
                                           body=Query(query).body,
                                           size=1000)

        return [cls.get(x['_id']) for x in res['hits']['hits']
                if x['_score'] > 0.3]

    def save(self):
        """Currently not supposed to save Records."""
        raise Exception('CirculationRecord is a Wrapper class for Record.')


class CirculationItem(CirculationObject, db.Model):
    """Data model to store bibliographic item information."""

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
    STATUS_UNAVAILABLE = 'unavailable'

    ADD_STATUS_BINDING = 'binding'
    ADD_STATUS_ON_ORDER = 'on_order'
    ADD_STATUS_REVIEW = 'review'

    EVENT_CREATE = 'item_created'
    EVENT_CHANGE = 'item_changed'
    EVENT_DELETE = 'item_deleted'
    EVENT_MISSING = 'item_missing'
    EVENT_RETURNED_MISSING = 'item_returned_missing'
    EVENT_IN_PROCESS = 'item_in_process'
    EVENT_PROCESS_RETURNED = 'item_process_returned'

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

    _all_field = ['record_id', 'isbn', 'barcode', 'title']

    _mappings = {'mappings': {
        'circulation_item': {
            '_all': {'enabled': True},
            'properties': {
                'id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'record_id': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'location_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'isbn': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'barcode': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'current_status': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'title': {
                    'type': 'string'},
                'record': {
                    'properties': {
                        'title': {
                            'type': 'string',
                            'copy_to': ['title']}
                        }
                    },
                }
            }
        }
        }

    @db.reconstructor
    def _init_on_load(self):
        # TODO: Don't know if there is a better way than None
        try:
            self.record = CirculationRecord.get(self.record_id)
        except Exception:
            self.record = None


class CirculationLoanCycle(CirculationObject, db.Model):
    """Data model to store loan information.

    Information associated with the loan cycle is stored in an object of this
    class.
    The assigned information include:
    * The corresponding user.
    * The corresponding item.
    * The desired and actual start and end date.
    """

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
    notes = db.Column(db.String(255))
    issued_date = db.Column(db.DateTime)
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    STATUS_ON_LOAN = 'on_loan'
    STATUS_REQUESTED = 'requested'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELED = 'canceled'

    STATUS_OVERDUE = 'overdue'

    EVENT_CREATE = 'clc_created'
    EVENT_CHANGE = 'clc_changed'
    EVENT_DELETE = 'clc_deleted'
    EVENT_CREATED_LOAN = 'clc_created_loan'
    EVENT_CREATED_REQUEST = 'clc_created_request'
    EVENT_TRANSFORMED_REQUEST = 'clc_transformed_request'
    EVENT_FINISHED = 'clc_finish'
    EVENT_CANCELED = 'clc_canceled'
    EVENT_UPDATED = 'clc_updated'
    EVENT_OVERDUE = 'clc_overdue'
    EVENT_OVERDUE_LETTER = 'clc_overdue_letter'
    EVENT_REQUEST_LOAN_EXTENSION = 'clc_request_loan_extension'
    EVENT_LOAN_EXTENSION = 'clc_loan_extension'

    DELIVERY_DEFAULT = 'pick_up'
    DELIVERY_PICK_UP = 'pick_up'
    DELIVERY_INTERNAL_MAIL = 'internal_mail'

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

    _mappings = {'mappings': {
        'circulation_loan_cycle': {
            '_all': {'enabled': True},
            'properties': {
                'id': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'group_uuid': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'end_date': {
                    'type': 'date'},
                }
            }
        }
        }


class CirculationUser(CirculationObject, db.Model):
    """Data model to store user information for invenio-circulation."""

    __tablename__ = 'circulation_user'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    invenio_user_id = db.Column(db.BigInteger)
    current_status = db.Column(db.String(255))
    ccid = db.Column(db.String(255))
    name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    mailbox = db.Column(db.String(255))
    division = db.Column(db.String(255))
    cern_group = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(255))
    notes = db.Column(db.String(255))
    user_group = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    GROUP_DEFAULT = 'default'

    EVENT_CREATE = 'user_created'
    EVENT_CHANGE = 'user_changed'
    EVENT_DELETE = 'user_deleted'
    EVENT_MESSAGED = 'user_messaged'

    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'

    _json_schema = {'type': 'object',
                    'title': 'User',
                    'properties': {
                        'id': {'type': 'integer'},
                        'invenio_user_id': {'type': 'integer'},
                        'ccid': {'type': 'string'},
                        'name': {'type': 'string'},
                        'address': {'type': 'string'},
                        'mailbox': {'type': 'string'},
                        'division': {'type': 'string'},
                        'cern_group': {'type': 'string'},
                        'email': {'type': 'string'},
                        'phone': {'type': 'string'},
                        'notes': {'type': 'string'},
                        'user_group': {'type': 'string'}
                        }
                    }

    _all_field = ['ccid', 'name', 'email', 'address', 'phone']

    _mappings = {'mappings': {
        'circulation_user': {
            '_all': {'enabled': True,
                     'index': 'not_analyzed'},
            'properties': {
                'id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'invenio_user_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'ccid': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'name': {
                    'type': 'string'},
                'email': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'address': {
                    'type': 'string'},
                'phone': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'mailbox': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'user_group': {
                    'type': 'string'},
                'notes': {
                    'type': 'string'},
                }
            }
        }
        }


class CirculationLocation(CirculationObject, db.Model):
    """Data model to store information regarding utilized locations.

    In the context of a library, this class stores information of those.
    """

    __tablename__ = 'circulation_location'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    code = db.Column(db.String(255))
    name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(255))
    type = db.Column(db.String(255))
    notes = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    EVENT_CREATE = 'location_created'
    EVENT_CHANGE = 'location_changed'
    EVENT_DELETE = 'location_deleted'

    TYPE_INTERNAL = 'internal'
    TYPE_EXTERNAL = 'external'
    TYPE_HIDDEN = 'hidden'
    TYPE_MAIN = 'main'

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

    _mappings = {'mappings': {
        'circulation_location': {
            '_all': {'enabled': True},
            'properties': {
                'id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'code': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'name': {
                    'type': 'string'},
                'notes': {
                    'type': 'string'},
                }
            }
        }
        }


class CirculationMailTemplate(CirculationObject, db.Model):
    """Data model to store E-mail templates."""

    __tablename__ = 'circulation_mail_template'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    template_name = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    header = db.Column(db.String(255))
    content = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    EVENT_CREATE = 'mail_template_created'
    EVENT_CHANGE = 'mail_template_changed'
    EVENT_DELETE = 'mail_template_deleted'

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

    _mappings = {'mappings': {
        'circulation_mail_template': {
            '_all': {'enabled': True},
            'properties': {
                'id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'template_name': {
                    'type': 'string'},
                'subject': {
                    'type': 'string'},
                'header': {
                    'type': 'string'},
                'content': {
                    'type': 'string'},
                }
            }
        }
        }


class CirculationLoanRule(CirculationObject, db.Model):
    """Data model to store loan rules definitions."""

    __tablename__ = 'circulation_loan_rule'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    name = db.Column(db.String(255))
    type = db.Column(db.String(255))
    loan_period = db.Column(db.Integer)
    holdable = db.Column(db.Boolean)
    home_pickup = db.Column(db.Boolean)
    renewable = db.Column(db.Boolean)
    automatic_recall = db.Column(db.Boolean)
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

    EVENT_CREATE = 'loan_rule_created'
    EVENT_CHANGE = 'loan_rule_changed'
    EVENT_DELETE = 'loan_rule_deleted'

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

    _mappings = {'mappings': {
        'circulation_loan_rule': {
            '_all': {'enabled': True},
            'properties': {
                'id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'name': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'type': {
                    'type': 'string',
                    'index': 'not_analyzed'},
                'loan_period': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'holdable': {
                    'type': 'boolean',
                    'index': 'not_analyzed'},
                'home_pickup': {
                    'type': 'boolean',
                    'index': 'not_analyzed'},
                'renewable': {
                    'type': 'boolean',
                    'index': 'not_analyzed'},
                'automatic_recall': {
                    'type': 'boolean',
                    'index': 'not_analyzed'},
                },
            }
        }
        }


class CirculationLoanRuleMatch(CirculationObject, db.Model):
    """Data model to store application conditions for CirculationLoanRules."""

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

    EVENT_CREATE = 'loan_rule_match_created'
    EVENT_CHANGE = 'loan_rule_match_changed'
    EVENT_DELETE = 'loan_rule_match_deleted'

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

    _mappings = {
            'mappings': {
                'circulation_loan_rule_match': {
                    '_all': {'enabled': True},
                    'properties': {
                        'id': {
                            'type': 'integer',
                            'index': 'not_analyzed'},
                        'loan_rule_id': {
                            'type': 'integer',
                            'index': 'not_analyzed'},
                        'item_type': {
                            'type': 'string',
                            'index': 'not_analyzed'},
                        'patron_type': {
                            'type': 'string',
                            'index': 'not_analyzed'},
                        'location_code': {
                            'type': 'string',
                            'index': 'not_analyzed'},
                        },
                    }
                }
            }


class CirculationEvent(CirculationObject, db.Model):
    """Data model to store events associated with invenio-circulation.

    Certain important actions will be stored as CirculationEvents. This class
    therefore carries information about the involved objects and the kind of
    event.
    """

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
    loan_rule_match_id = db.Column(
            db.BigInteger, db.ForeignKey('circulation_loan_rule_match.id',
                                         ondelete="SET NULL"))
    loan_rule_match = db.relationship('CirculationLoanRuleMatch')
    event = db.Column(db.String(255))
    description = db.Column(db.String(255))
    creation_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    _data = db.Column(db.LargeBinary)

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

    _mappings = {'mappings': {
        'circulation_event': {
            '_all': {'enabled': True},
            'properties': {
                'id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'user_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'item_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'loan_cycle_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'location_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'loan_rule_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'mail_template_id': {
                    'type': 'integer',
                    'index': 'not_analyzed'},
                'event': {
                    'type': 'string'},
                'global_fulltext': {
                    'type': 'string'},
                }
            }
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
            ('Loan Rule', 'loan_rule', CirculationLoanRule),
            ('Loan Rule Match', 'loan_rule_match', CirculationLoanRuleMatch)]
