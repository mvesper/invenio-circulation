# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""invenio-circulation entity interface."""

import json

from flask import Blueprint, render_template, flash

from invenio_circulation.views.utils import (
        datetime_serial, send_signal, flatten, extract_params)
from invenio_circulation.acl import circulation_admin_permission as cap

blueprint = Blueprint('entity', __name__, url_prefix='/circulation',
                      template_folder='../templates',
                      static_folder='../static')


@blueprint.route('/entities')
@cap.require(403)
def entities_overview():
    """User interface showing all involved entities."""
    from invenio_circulation.signals import entities_overview

    entities = flatten(send_signal(entities_overview,
                                   'entities_overview', None))

    return render_template('entities/overview.html',
                           active_nav='entities', entities=entities)


@blueprint.route('/entities/<entity>')
@cap.require(403)
def entities_hub(entity):
    """User interface providing the search for the given entity."""
    return render_template('entities/entity_hub.html',
                           active_nav='entities', entity=entity)


@blueprint.route('/entities/action/search/<entity>/')
@blueprint.route('/entities/action/search/<entity>/<search>')
@cap.require(403)
def entity_hub_search(entity, search=''):
    """User interface showing the search result for the given entity."""
    from invenio_circulation.signals import entities_hub_search

    entities, template = send_signal(entities_hub_search, entity, search)[0]

    return render_template(template,
                           active_nav='entities',
                           entities=entities, entity=entity)


@blueprint.route('/entities/<entity>/<id>')
@cap.require(403)
def entity(entity, id):
    """User interface showing the specified entity and additional info."""
    from invenio_circulation.signals import (
            entity as _entity,
            entity_suggestions as _entity_suggestions,
            entity_aggregations as _entity_aggregations)

    obj = send_signal(_entity, entity, id)[0]
    try:
        suggestions_config = send_signal(_entity_suggestions, entity, None)[0]
    except IndexError:
        suggestions_config = {}
    aggregations = send_signal(_entity_aggregations, entity, id)

    editor_data = json.dumps(obj.jsonify(), default=datetime_serial)
    editor_schema = json.dumps(obj._json_schema, default=datetime_serial)

    return render_template('entities/entity_detail.html',
                           active_nav='entities',
                           editor_data=editor_data,
                           editor_schema=editor_schema,
                           aggregations=flatten(aggregations),
                           suggestions_config=json.dumps(suggestions_config))


@blueprint.route('/entities/action/create/<entity>')
@cap.require(403)
def entity_new(entity):
    """User interface to create a new entity."""
    from invenio_circulation.signals import (
            entity_class,
            entity_suggestions as _entity_suggestions)

    clazz = send_signal(entity_class, entity, None)[0]
    suggestions_config = send_signal(_entity_suggestions, entity, None)[0]

    editor_schema = clazz._json_schema
    # entering certain values is going to break and doesn't make sense,
    # so they will be removed here
    for key in ['id', 'group_uuid', 'creation_date']:
        try:
            del editor_schema['properties'][key]
        except KeyError:
            pass
    editor_schema = json.dumps(editor_schema, default=datetime_serial)

    return render_template('entities/entity_create.html',
                           active_nav='entities', obj={}, entity=entity,
                           editor_data={},
                           editor_schema=editor_schema,
                           suggestions_config=json.dumps(suggestions_config))


@blueprint.route('/api/entity/search', methods=['POST'])
@cap.require(403)
@extract_params
def api_entity_search(entity, search):
    """API to search for objects of the given entity."""
    from invenio_circulation.signals import entity_class

    clazz = send_signal(entity_class, entity, None)[0]
    objs = clazz.search(search)
    return json.dumps([x.jsonify() for x in objs], default=datetime_serial)


@blueprint.route('/api/entity/search_autocomplete', methods=['POST'])
@cap.require(403)
@extract_params
def api_entity_search_autocomplete(entity, search):
    """API to search (simplified) for objects of the given entity."""
    from invenio_circulation.signals import entity_autocomplete_search

    q = {'query': {'bool': {'should': {'match': {'content_ngram': search}}}}}

    res = send_signal(entity_autocomplete_search, entity, search)[0]
    return json.dumps(res)


@blueprint.route('/api/entity/create', methods=['POST'])
@cap.require(403)
@extract_params
def api_entity_create(entity, data):
    """API to create an object of the given entity."""
    from invenio_circulation.signals import entity_name, circ_apis

    name = send_signal(entity_name, entity, None)[0]
    api = send_signal(circ_apis, entity, None)[0]

    entity = api.create(**data)

    flash('Successfully created a new {0} with id {1}.'.format(name,
                                                               entity.id))
    return ('', 200)


@blueprint.route('/api/entity/update', methods=['POST'])
@cap.require(403)
@extract_params
def api_entity_update(id, entity, data):
    """API to update an object of the given entity."""
    from invenio_circulation.signals import (
            entity_class, entity_name, circ_apis)

    clazz = send_signal(entity_class, entity, None)[0]
    name = send_signal(entity_name, entity, None)[0]
    api = send_signal(circ_apis, entity, None)[0]

    api.update(clazz.get(id), **data)

    flash('Successfully updated the {0} with id {1}.'.format(name, id))
    return ('', 200)


@blueprint.route('/api/entity/delete', methods=['POST'])
@cap.require(403)
@extract_params
def api_entity_delete(id, entity):
    """API to delete the specified object."""
    from invenio_circulation.signals import (
            entity_class, entity_name, circ_apis)

    clazz = send_signal(entity_class, entity, None)[0]
    name = send_signal(entity_name, entity, None)[0]
    api = send_signal(circ_apis, entity, None)[0]

    api.delete(clazz.get(id))

    flash('Successfully updated the {0} with id {1}.'.format(name, id))
    return ('', 200)
