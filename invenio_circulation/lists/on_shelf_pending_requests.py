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

"""invenio-circulation list to handle items on shelf with pending requests."""

from flask import render_template


class OnShelfPendingRequests(object):
    """invenio-circulation list class to provide the list user interface."""

    @classmethod
    def entrance(cls):
        """List class function providing second stage user interface.

        Displays the loan cycles for items on shelf with pending requests.
        """
        from invenio_circulation.models import (CirculationItem,
                                                CirculationLoanCycle)

        query = 'current_status:{0} AND item.current_status:{1}'.format(
                CirculationLoanCycle.STATUS_REQUESTED,
                CirculationItem.STATUS_ON_SHELF)

        clcs = CirculationLoanCycle.search(query)
        return render_template('lists/on_shelf_pending_requests.html',
                               active_nav='lists', clcs=clcs)

    @classmethod
    def detail(cls, query):
        """List class function providing second stage user interface.

        Empty.
        """
        pass
