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

"""Persistent identifier minters."""

from __future__ import absolute_import, unicode_literals

import uuid

from .providers import CirculationItemProvider, CirculationLoanCycleProvider, \
        CirculationLocationProvider


def circulation_location_minter(record_uuid, data):
    """Mint a circulation identifier."""
    assert 'control_number' not in data and 'uuid' not in data
    provider = CirculationLocationProvider.create(
        object_type='rec',
        object_uuid=record_uuid,
        pid_value=str(record_uuid),
    )
    data['control_number'] = provider.pid.pid_value
    data['uuid'] = str(record_uuid)

    return provider.pid

def circulation_loan_cycle_minter(record_uuid, data):
    """Mint a circulation identifier."""
    assert 'control_number' not in data and 'uuid' not in data
    provider = CirculationLoanCycleProvider.create(
        object_type='rec',
        object_uuid=record_uuid,
        pid_value=str(record_uuid),
    )
    data['control_number'] = provider.pid.pid_value
    data['uuid'] = str(record_uuid)

    return provider.pid


def circulation_item_minter(record_uuid, data):
    """Mint a circulation identifier."""
    assert 'control_number' not in data and 'uuid' not in data
    provider = CirculationItemProvider.create(
        object_type='rec',
        object_uuid=record_uuid,
        recid=data['record']['control_number']
    )
    data['control_number'] = provider.pid.pid_value
    data['uuid'] = str(record_uuid)

    return provider.pid
