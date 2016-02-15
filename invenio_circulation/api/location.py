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
from invenio_circulation.signals import (circulation_location_created,
                                         circulation_location_deleted,
                                         circulation_location_updated)
from invenio_circulation.transaction import persist
from invenio_db import db


@persist
def create(name, address, notes):
    """Create a CirculationLoanLocation object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    data = {'location': {'sublocation_or_collection': name,
                         'address': address,
                         'nonpublic_notes': notes}}
    cl = models.CirculationLocation.create(data)
    return cl
