# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
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

"""List the access actions used for authorization."""

import pkg_resources
from flask_principal import ActionNeed

circulation_admin_access = ActionNeed('circulationadmin')


def admin_permission_factory():
    """Factory for creating a permission for an admin.

    :returns: Permission instance.
    """
    try:
        pkg_resources.get_distribution('invenio-access')
        from invenio_access.permissions import DynamicPermission as Permission
    except pkg_resources.DistributionNotFound:
        from flask_principal import Permission

    return Permission(circulation_admin_access)
