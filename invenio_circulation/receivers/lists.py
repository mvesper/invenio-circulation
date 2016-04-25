# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""invenio-circulation receiver to handle list signals."""

from invenio_circulation.signals import lists_overview, lists_class


def _lists_overview(sender, data):
    return {'name': 'lists',
            'result': [('Items on loan with pending requests',
                        'on_loan_pending_requests'),
                       ('Items on shelf with pending requests',
                        'on_shelf_pending_requests'),
                       ('Overdue items with pending requests',
                        'overdue_pending_requests'),
                       ('Overdue Items', 'overdue_items'),
                       ('Latest Loans', 'latest_loans')]}


def _lists_class(link, data):
    from invenio_circulation.lists.on_loan_pending_requests import (
            OnLoanPendingRequests)
    from invenio_circulation.lists.on_shelf_pending_requests import (
            OnShelfPendingRequests)
    from invenio_circulation.lists.overdue_pending_requests import (
            OverduePendingRequests)
    from invenio_circulation.lists.overdue_items import OverdueItems
    from invenio_circulation.lists.latest_loans import LatestLoans

    clazzes = {'latest_loans': LatestLoans,
               'overdue_items': OverdueItems,
               'on_shelf_pending_requests': OnShelfPendingRequests,
               'on_loan_pending_requests': OnLoanPendingRequests,
               'overdue_pending_requests': OverduePendingRequests}

    return {'name': 'lists', 'result': clazzes.get(link)}

lists_overview.connect(_lists_overview)
lists_class.connect(_lists_class)
