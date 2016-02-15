# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""Signal definitions."""

from blinker import Namespace


_signals = Namespace()

circulation_item_loaned = _signals.signal('circulation_item_loaned')
circulation_item_requested = _signals.signal('circulation_item_requested')
circulation_item_returned = _signals.signal('circulation_item_returned')

circulation_item_created = _signals.signal('circulation_item_created')
circulation_item_updated = _signals.signal('circulation_item_updated')
circulation_item_deleted = _signals.signal('circulation_item_deleted')
circulation_item_lost = _signals.signal('circulation_item_lost')
circulation_item_missing_returned = _signals.signal(
                                        'circulation_item_missing_returned')
circulation_item_processed = _signals.signal(
                                        'circulation_item_processed')
circulation_item_process_returned = _signals.signal(
                                        'circulation_item_process_returned')

circulation_loan_cycle_created = _signals.signal(
                                        'circulation_loan_cycle_created')
circulation_loan_cycle_updated = _signals.signal(
                                        'circulation_loan_cycle_updated')
circulation_loan_cycle_deleted = _signals.signal(
                                        'circulation_loan_cycle_deleted')
circulation_loan_cycle_canceled = _signals.signal(
                                        'circulation_loan_cycle_canceled')
circulation_loan_cycle_overdued = _signals.signal(
                                        'circulation_loan_cycle_overdued')
circulation_loan_cycle_extended = _signals.signal(
                                        'circulation_loan_cycle_extended')
circulation_loan_cycle_transformed = _signals.signal(
                                        'circulation_loan_cycle_transformed')

circulation_location_created = _signals.signal('circulation_location_created')
circulation_location_updated = _signals.signal(
                                        'circulation_location_updated')
circulation_location_deleted = _signals.signal('circulation_location_deleted')
