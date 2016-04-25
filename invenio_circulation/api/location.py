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

"""invenio-circulation api responsible for CirculationLocation handling."""

import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(code, name, notes):
    """Create a CirculationLoanLocation object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    cl = models.CirculationLocation.new(code=code, name=name, notes=notes)
    create_event(location_id=cl.id,
                 event=models.CirculationLocation.EVENT_CREATE)
    return cl


def update(cl, **kwargs):
    """Update a CirculationLoanLocation object."""
    current_items, changed = _update(cl, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(location_id=cl.id,
                     event=models.CirculationLocation.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(cl):
    """Delete a CirculationLoanLocation object."""
    create_event(location_id=cl.id,
                 event=models.CirculationLocation.EVENT_DELETE)
    cl.delete()


schema = {}
