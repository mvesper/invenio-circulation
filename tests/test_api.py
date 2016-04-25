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

from utils import (_create_dates, _create_test_data, _delete_test_data,
                   current_app, rec_uuids, state)


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

        _delete_test_data(ce)


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

        _delete_test_data(ce)


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
