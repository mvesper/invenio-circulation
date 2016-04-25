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

"""invenio-circulation list to handle latest loans."""

import datetime

from flask import render_template


class LatestLoans(object):
    """invenio-circulation list class to provide the list user interface."""

    @classmethod
    def entrance(cls):
        """List class function providing first stage user interface.

        Displays a user interface to select the desired period of time.
        """
        end_date = datetime.date.today()
        start_date = datetime.date.today() - datetime.timedelta(weeks=1)

        return render_template('lists/latest_loans_entrance.html',
                               active_nav='lists',
                               link='latest_loans',
                               start_date=start_date, end_date=end_date)

    @classmethod
    def detail(cls, start_date, end_date):
        """List class function providing second stage user interface.

        Displays the loan cycles in the desired time period.
        """
        from invenio_circulation.models import CirculationLoanCycle

        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

        def check(clc):
            return start_date <= clc.start_date <= end_date

        clcs = [x for x in CirculationLoanCycle.get_all() if check(x)]

        return render_template('lists/latest_loans_detail.html',
                               active_nav='lists', clcs=clcs,
                               link='latest_loans',
                               start_date=start_date, end_date=end_date)
