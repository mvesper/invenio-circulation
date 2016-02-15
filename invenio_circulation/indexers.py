# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""CirculationObject indexers."""

from __future__ import unicode_literals

import copy

from invenio_indexer.api import RecordIndexer


class CirculationLoanCycleIndexer(RecordIndexer):
    """Indexer for CirculationLoanCycle records."""

    def index(self, record):
        """Index a CirculationLoanCycle record."""
        _rec = copy.deepcopy(record)
        rec = _rec['local_data']

        rec['user'] = {'id': rec['user'].id,
                       'email': rec['user'].email,
                       'profile': {
                           'username': rec['user'].profile.username,
                           'full_name': rec['user'].profile.full_name}}

        rec['start_date'] = rec['start_date'].isoformat()
        rec['end_date'] = rec['end_date'].isoformat()
        rec['desired_start_date'] = rec['desired_start_date'].isoformat()
        rec['desired_end_date'] = rec['desired_end_date'].isoformat()
        try:
            rec['requested_extension_end_date'] = (
                    rec['requested_extension_end_date'].isoformat())
        except AttributeError:
            rec['requested_extension_end_date'] = None

        rec['issued_date'] = rec['issued_date'].isoformat()

        super(CirculationLoanCycleIndexer, self).index(_rec)
