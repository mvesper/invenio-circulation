# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Module user search tests."""

import json

from flask import url_for
from invenio_accounts.models import User


def test_user_search(app, db, access_token):
    """Test REST API for circulation specific user search."""
    # The access_token fixture generates a user
    user = User.query.all()[0]
    with app.test_request_context():
        with app.test_client() as client:
            # Search while not being authorized
            url = url_for('circulation_rest.circulation_user_resource')
            url += '?q={0}'.format(user.id + 1)
            url += '&access_token=foo'
            res = client.get(url)

            assert res.status_code == 401

            # Search for non existing user
            url = url_for('circulation_rest.circulation_user_resource')
            url += '?q={0}'.format(user.id + 1)
            url += '&access_token=' + access_token
            res = client.get(url)

            assert res.status_code == 200
            assert len(json.loads(res.data.decode('utf-8'))) == 0

            # Search for existing user
            url = url_for('circulation_rest.circulation_user_resource')
            url += '?q={0}'.format(user.id)
            url += '&access_token=' + access_token
            res = client.get(url)

            assert res.status_code == 200
            assert len(json.loads(res.data.decode('utf-8'))) == 1
