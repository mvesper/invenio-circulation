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

"""invenio-circulation list to handle overdue loans."""

from flask import render_template


class OverduePendingRequests(object):
    """invenio-circulation list class to provide the list user interface."""

    @classmethod
    def entrance(cls):
        """List class function providing second stage user interface.

        Displays overdue loans with pending requests.
        """
        from invenio_db import db
        from invenio_circulation.models import CirculationLoanCycle

        # Get overdue CLC item ids
        over_status = CirculationLoanCycle.STATUS_OVERDUE
        over_ids = (db.session.query(CirculationLoanCycle.item_id)
                    .filter(CirculationLoanCycle.additional_statuses
                            .contains(over_status))
                    .distinct())

        # Get requested CLC with those ids
        CLC = CirculationLoanCycle
        req_status = CirculationLoanCycle.STATUS_REQUESTED
        req_ids = (db.session.query(CirculationLoanCycle.id)
                   .filter(db.and_(CLC.current_status == req_status,
                                   CLC.item_id.in_(over_ids)))
                   .distinct())
        req_ids = set(x for x in req_ids)

        clcs = [CirculationLoanCycle.get(id[0]) for id in req_ids]

        return render_template('lists/overdue_items.html',
                               active_nav='lists', clcs=clcs)

    @classmethod
    def detail(cls, query):
        """List class function providing second stage user interface.

        Empty
        """
        pass
