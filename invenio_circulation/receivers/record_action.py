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

"""invenio-circulation receiver to handle record signals."""

from invenio_circulation.signals import record_actions


def _record_actions(sender, data):
    from flask import render_template
    from invenio_circulation.models import CirculationItem

    res = None
    if CirculationItem.search('record_id:{0}'.format(data['record_id'])):
        res = render_template('search/library_copies.html', **data)

    return {'name': 'circulation', 'result': res}


record_actions.connect(_record_actions)
