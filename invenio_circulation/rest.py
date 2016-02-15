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

"""invenio-circulation interface."""

from flask import Blueprint, abort

from invenio_records_rest.utils import obj_or_import_string
from invenio_rest import ContentNegotiatedMethodView


def create_blueprint(endpoints):
    """Create invenio-circulation blueprint."""
    blueprint = Blueprint(
        'circulation_rest',
        __name__,
        static_folder='./static',
        template_folder='./templates',
        url_prefix='',
    )

    for endpoint, options in endpoints.items():
        if 'record_serializers' in options:
            serializers = options.get('record_serializers')
            serializers = {mime: obj_or_import_string(func)
                           for mime, func in serializers.items()}
        else:
            serializers = {}

        resolver = obj_or_import_string(options['resolver'])

        circulation_resource = CirculationResource.as_view(
            endpoint,
            serializers=serializers,
            resolver=resolver,
            default_media_type=options['default_media_type']
        )

        blueprint.add_url_rule(
            options['item_route'],
            view_func=circulation_resource,
            methods=['GET'],
        )

    return blueprint


class CirculationResource(ContentNegotiatedMethodView):
    """MethodView implementation."""

    def __init__(self, serializers, resolver, default_media_type):
        """Constructor."""
        super(CirculationResource, self).__init__(
            serializers, default_media_type=default_media_type)

        self.resolver = resolver

    def get(self, pid_value):
        """Get deposit/depositions/:id/files/:key."""
        try:
            obj = self.resolver(pid_value)
            return self.make_response(pid_value, obj or abort(404))
        except Exception:
            abort(404)
