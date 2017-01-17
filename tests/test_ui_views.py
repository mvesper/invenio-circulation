# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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

"""Module UI views tests."""

from flask import url_for


def test_receiver_base(app, build_assets, user):
    """Test UI view index page."""
    with app.test_request_context():
        with app.test_client() as client:
            # admin page
            url = url_for('circulation.index')
            res = client.get(url)
            assert res.status_code == 200

            # user hub page
            url = url_for('circulation.user_hub')
            res = client.get(url)
            assert res.status_code == 200

            # admin user hub page
            url = url_for('circulation.admin_user_view', user_id=user.id)
            res = client.get(url)
            assert res.status_code == 200

            # admin user hub page not existing user_id
            url = url_for('circulation.admin_user_view', user_id=user.id+1000)
            res = client.get(url)
            assert res.status_code == 404
