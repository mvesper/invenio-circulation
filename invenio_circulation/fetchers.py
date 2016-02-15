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

"""Persistent identifier fetchers."""

from __future__ import absolute_import, unicode_literals

from invenio_pidstore.fetchers import FetchedPID

from .providers import CirculationItemProvider, CirculationLoanCycleProvider, \
        CirculationLocationProvider


def _circulation_fetcher(control_number, provider):
    return FetchedPID(provider=provider, pid_type=provider.pid_type,
                      pid_value=str(control_number))


def circulation_item_fetcher(control_number):
    """Fetch a circulation item identifier."""
    return _circulation_fetcher(control_number, CirculationItemProvider)


def circulation_loan_cycle_fetcher(control_number):
    """Fetch a circulation loan cycle identifier."""
    return _circulation_fetcher(control_number, CirculationLoanCycleProvider)


def circulation_location_fetcher(control_number):
    """Fetch a circulation location identifier."""
    return _circulation_fetcher(control_number, CirculationLocationProvider)
