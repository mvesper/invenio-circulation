# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Invenio-Circulation REST interface."""

import json
from flask import Blueprint, request
from sqlalchemy import String, cast
from invenio_accounts.models import User
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_records_rest.views import \
    create_url_rules as records_rest_url_rules
from invenio_rest import ContentNegotiatedMethodView


def circulation_user_serializer(*args, **kwargs):
    """Basic serializer for invenio_accounts.models.User data."""
    return json.dumps([{'id': u.id, 'email': u.email} for u in args])


def create_blueprint(endpoints):
    """Create invenio-circulation REST blueprint."""
    blueprint = Blueprint(
        'circulation_rest',
        __name__,
        static_folder='./static',
        template_folder='./templates',
        url_prefix='',
    )

    for endpoint, options in endpoints.items():
        for rule in records_rest_url_rules(endpoint, **options):
            blueprint.add_url_rule(**rule)

    circulation_resource = CirculationUserResource.as_view(
        'circulation_user_resource',
        serializers={'application/json': circulation_user_serializer},
        default_media_type='application/json'
    )

    blueprint.add_url_rule(
        '/circulation/users/',
        view_func=circulation_resource,
        methods=['GET'],
    )

    return blueprint


class CirculationUserResource(ContentNegotiatedMethodView):
    """MethodView implementation."""

    def __init__(self, serializers, default_media_type):
        """Constructor."""
        super(CirculationUserResource, self).__init__(
            serializers, default_media_type=default_media_type)

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    def get(self):
        """Get circulation/users/?q=."""
        query = request.args.get('q')
        return list(User.query.filter(
            (User.email == query) |
            (cast(User.id, String) == query)
        ))
