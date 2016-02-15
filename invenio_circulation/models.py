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

from __future__ import unicode_literals

import datetime
import uuid

from elasticsearch_dsl.query import QueryString
from flask import current_app, url_for
from invenio_accounts.models import User
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from invenio_search import RecordsSearch

from .indexers import CirculationLoanCycleIndexer
from .minters import circulation_item_minter, circulation_loan_cycle_minter, \
        circulation_location_minter
from .signals import circulation_item_created, circulation_item_deleted, \
        circulation_item_updated, circulation_loan_cycle_created, \
        circulation_loan_cycle_deleted, circulation_loan_cycle_updated, \
        circulation_location_created, circulation_location_deleted, \
        circulation_location_updated
from .transaction import index


class CirculationObject(Record):
    """Base class of invenio-circulation entities.

    Provides general database and elasticsearch functionality.
    """

    indexer = RecordIndexer()
    pid_type = None

    @property
    def pid(self):
        """Return an instance of circulation PID."""
        return PersistentIdentifier.get(self.pid_type, self['control_number'])

    @classmethod
    def _minter(cls, uuid, rec):
        raise Exception('Override this function using the needed minter.')

    @classmethod
    def create(cls, data, id_=None):
        """Create a CirculationObject."""
        json_schema = current_app.extensions['invenio-jsonschemas']
        data.setdefault('$schema',
                        {'$ref': json_schema.path_to_url(cls.__schema__)})

        if 'uuid' not in data:
            id_ = id_ or uuid.uuid4()
            cls._minter(id_, data)

        return super(CirculationObject, cls).create(data, id_)

    def delete(self, force=False):
        """Delete the object."""
        self.pid.delete()
        return super(CirculationObject, self).delete(force=force)

    @classmethod
    def search(cls, query):
        """Search for objects using the invenio query syntax."""
        search = RecordsSearch()
        tmp = search.index().index(cls.__index__)
        if query:
            tmp = tmp.query(QueryString(query=query))

        return [cls.get_record(x['uuid']) for x in tmp.execute()]

    @classmethod
    def mechanical_query(cls, query):
        """Search for objects in the database using key-values pairs."""
        def handle_key(key):
            keys = key.split('.') if '.' in key else [key]
            return ', '.join(keys)

        query_base = "json#>>'{{{0}}}' = '{1}'"
        where = ' and '.join([query_base.format(handle_key(key), value)
                              for key, value in query.items()])
        query = 'select id from records_metadata where {0};'.format(where)

        return [cls.get_record(x[0]) for x in db.engine.execute(query)]


class CirculationItem(CirculationObject):
    """Data model to store bibliographic item information."""

    __index__ = 'circulation-item'
    __schema__ = 'circulation/item.json'

    pid_type = 'ciritm'

    GROUP_BOOK = 'book'

    STATUS_ON_SHELF = 'on_shelf'
    STATUS_ON_LOAN = 'on_loan'
    STATUS_IN_PROCESS = 'in_process'
    STATUS_MISSING = 'missing'
    STATUS_UNAVAILABLE = 'unavailable'

    ADD_STATUS_BINDING = 'binding'
    ADD_STATUS_ON_ORDER = 'on_order'
    ADD_STATUS_REVIEW = 'review'

    @classmethod
    def _minter(cls, uuid, rec):
        return circulation_item_minter(uuid, rec)

    @classmethod
    @index
    def create(cls, data, id_=None):
        """Create a CirculationItem."""
        saves = cls._prepare(data)
        rec = super(CirculationItem, cls).create(data, id_)
        rec.update(saves)

        circulation_item_created.send(rec)

        return rec

    @index
    def commit(self, *args, **kwargs):
        """Add the object to the database session."""
        saves = self._prepare(self)
        rec = super(CirculationItem, self).commit(*args, **kwargs)
        rec.update(saves)

        circulation_item_updated.send(rec)

        return rec

    @classmethod
    def get_record(cls, id, with_deleted=False):
        """Get the CirculationItem with the given id."""
        rec = super(CirculationItem, cls).get_record(id, with_deleted)
        rec.update(cls._dereference(rec))

        return rec

    @index(delete=True)
    def delete(self, force=False):
        """Delete the object."""
        circulation_item_deleted.send(self)
        return super(CirculationItem, self).delete(force=force)

    @classmethod
    def _prepare(self_or_cls, data):
        if 'location' in data['location']:
            tmp = data['location'].copy()
            tmp.update({
                'classification_part': data['location']['classification_part'],
                'sublocation_or_collection':
                    data['location']['location']['sublocation_or_collection'],
                'address': data['location']['location']['address'],
                'nonpublic_notes':
                    data['location']['location']['nonpublic_notes']})
            del tmp['location']
        else:
            tmp = data['location']

        # Before amending the record, save for restoration
        saves = {'location': tmp, 'record': data['record']}

        # Amend the record and location with the corresponding references
        urls = self_or_cls._get_reference_urls(data)
        data['location'] = {'$ref': urls['location'],
                            'classification_part': data['location'][
                                                        'classification_part']
                            }
        data['record'] = {'$ref': urls['record'],
                          'control_number': data['record']['control_number']}

        return saves

    @classmethod
    def _dereference(cls, rec):
        objs = {}
        if '$ref' not in rec['location'] and '$ref' not in rec['record']:
            # This happens for consecutive *get_record* calls
            return objs

        # Get the CirculationLocation
        uuid = rec['location']['$ref'].split('/')[-1]
        loc = CirculationLocation.get_record(uuid).copy()
        tmp = {'classification_part': rec['location'][
                                          'classification_part'],
               'sublocation_or_collection': loc['location'][
                                                'sublocation_or_collection'],
               'address': loc['location']['address'],
               'nonpublic_notes': loc['location']['nonpublic_notes']}
        loc.update(tmp)
        del loc['location']
        objs['location'] = loc

        # Get the Record
        control_number = rec['record']['$ref'].split('/')[-1]
        pid = PersistentIdentifier.get('recid', control_number)
        objs['record'] = Record.get_record(pid.object_uuid)

        return objs

    @classmethod
    def _get_reference_urls(cls, rec):
        return {'location': url_for('circulation_rest.location',
                                    pid_value=rec['location']['uuid']),
                'record': 'http://{0}/api/record/{1}'.format(
                            current_app.config['SERVER_NAME'],
                            rec['record']['control_number'])}


class CirculationLoanCycle(CirculationObject):
    """Data model to store loan information.

    Information associated with the loan cycle is stored in an object of this
    class.
    The assigned information include:
    * The corresponding user.
    * The corresponding item.
    * The desired and actual start and end date.
    """

    __index__ = 'circulation-loan_cycle'
    __schema__ = 'circulation/loan_cycle.json'

    indexer = CirculationLoanCycleIndexer()
    pid_type = 'cirlc'

    STATUS_ON_LOAN = 'on_loan'
    STATUS_REQUESTED = 'requested'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELED = 'canceled'
    STATUS_OVERDUE = 'overdue'

    DELIVERY_PICK_UP = 'pick_up'
    DELIVERY_INTERNAL_MAIL = 'internal_mail'
    DELIVERY_DEFAULT = DELIVERY_PICK_UP

    @classmethod
    def _minter(cls, uuid, rec):
        return circulation_loan_cycle_minter(uuid, rec)

    @classmethod
    @index
    def create(cls, data, id_=None):
        """Create a CirculationLoanCycle."""
        data['local_data']['issued_date'] = datetime.datetime.now()
        saves = cls._prepare(data)
        rec = super(CirculationLoanCycle, cls).create(data, id_)
        rec['local_data'].update(saves)

        circulation_loan_cycle_created.send(rec)

        return rec

    @classmethod
    def get_record(cls, id, with_deleted=False):
        """Get the CirculationLoanCycle with the given id."""
        rec = super(CirculationLoanCycle, cls).get_record(id, with_deleted)
        vals = cls._dereference(rec)
        rec['local_data'].update(vals)

        return rec

    @index
    def commit(self, *args, **kwargs):
        """Add the object to the database session."""
        saves = self._prepare(self)
        rec = super(CirculationLoanCycle, self).commit(*args, **kwargs)
        self['local_data'].update(saves)

        circulation_loan_cycle_updated.send(rec)

        return rec

    @index(delete=True)
    def delete(self, force=False):
        """Delete the object."""
        circulation_loan_cycle_deleted.send(self)
        return super(CirculationLoanCycle, self).delete(force=force)

    @classmethod
    def _prepare(self_or_cls, data):
        saves = data['local_data'].copy()
        data = data['local_data']

        try:
            reed = data['requested_extension_end_date'].isoformat()
        except Exception:
            reed = None

        def iso(date):
            return date.isoformat()

        vals = {'item': {'$ref': url_for('circulation_rest.item',
                                         pid_value=data['item'][
                                                        'control_number']),
                         'uuid': data['item']['uuid']},
                'user': {'id': data['user'].id,
                         'email': data['user'].email,
                         'profile': {
                             'username': data['user'].profile.username,
                             'full_name': data['user'].profile.full_name}},
                'start_date': iso(data['start_date']),
                'end_date': iso(data['end_date']),
                'desired_start_date': iso(data['desired_start_date']),
                'desired_end_date': iso(data['desired_end_date']),
                'requested_extension_end_date': reed,
                'issued_date': iso(data['issued_date'])
                }

        data.update(vals)

        return saves

    @classmethod
    def _dereference(cls, data):
        data = data['local_data']

        if type(data['user']) == User:
            # Happens when *get_record* gets called multiple times
            return {}

        def stp(date_string, date_format, to_date=True):
            d = datetime.datetime.strptime(date_string, date_format)
            return d.date() if to_date else d

        df = '%Y-%m-%d'
        dtf = '%Y-%m-%dT%H:%M:%S.%f'

        try:
            reed = stp(data['requested_extension_end_date'], df)
        except Exception:
            reed = None

        return {'item': CirculationItem.get_record(data['item']['uuid']),
                'user': User.query.get(data['user']['id']),
                'start_date': stp(data['start_date'], df),
                'end_date': stp(data['end_date'], df),
                'desired_start_date': stp(data['desired_start_date'], df),
                'desired_end_date': stp(data['desired_end_date'], df),
                'requested_extension_end_date': reed,
                'issued_date': stp(data['issued_date'], dtf, False)}


class CirculationLocation(CirculationObject):
    """Data model to store information regarding utilized locations.

    In the context of a library, this class stores information of those.
    """

    __index__ = 'circulation-location'
    __schema__ = 'circulation/location.json'

    pid_type = 'cirloc'

    TYPE_INTERNAL = 'internal'
    TYPE_EXTERNAL = 'external'
    TYPE_HIDDEN = 'hidden'
    TYPE_MAIN = 'main'

    @classmethod
    def _minter(cls, uuid, rec):
        return circulation_location_minter(uuid, rec)

    @classmethod
    @index
    def create(cls, data, id_=None):
        """Create a CirculationLocation."""
        circulation_location_created.send(data)
        return super(CirculationLocation, cls).create(data, id_)

    @index
    def commit(self, *args, **kwargs):
        """Add the object to the database session."""
        circulation_location_updated.send(self)
        return super(CirculationLocation, self).commit(*args, **kwargs)

    @index(delete=True)
    def delete(self, force=False):
        """Delete the object."""
        circulation_location_deleted.send(self)
        return super(CirculationLocation, self).delete(force=force)


class CirculationItemIdentifier(db.Model):
    """Sequence generator for CirculationItem identifiers."""

    __tablename__ = 'circulation_item_id'

    recid = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"),
                      primary_key=True)
    count = db.Column(db.Integer())

    @classmethod
    def next(cls, recid):
        """Return next available record identifier."""
        try:
            obj = cls.query.filter(cls.recid == recid)[0]
            obj.count += 1
        except:
            with db.session.begin_nested():
                obj = cls(recid=recid, count=0)
                db.session.add(obj)

        return obj.count
