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

"""Signal definitions."""

from blinker import Namespace


cs = Namespace()

save_entity = cs.signal('save_entity')
get_entity = cs.signal('get_entity')

entities_overview = cs.signal('entities_overview')
entities_hub_search = cs.signal('entities_hub_search')
entity = cs.signal('entity')
entity_suggestions = cs.signal('entity_suggestions')
entity_aggregations = cs.signal('entity_aggregations')

entity_class = cs.signal('entity_class')
entity_name = cs.signal('entity_name')
entity_new = cs.signal('entity_new')
entity_create = cs.signal('entity_create')
entity_update = cs.signal('entity_update')
entity_delete = cs.signal('entity_delete')
entity_autocomplete_search = cs.signal('entity_autocomplete_search')

lists_overview = cs.signal('lists_overview')
lists_class = cs.signal('lists_class')

item_returned = cs.signal('item_returned')

user_current_holds = cs.signal('user_current_holds')
user_current_holds_action = cs.signal('user_current_holds_action')
get_circulation_user_info = cs.signal('get_circulation_user_info')

# CIRCULATION

circulation_current_state = cs.signal('circulation_current_state')
circulation_search = cs.signal('circulation_search')
circulation_state = cs.signal('circulation_state')
circulation_actions = cs.signal('circulation_actions')
circulation_main_actions = cs.signal('circulation_main_actions')
circulation_other_actions = cs.signal('circulation_other_actions')

try_action = cs.signal('try_action')
run_action = cs.signal('run_action')

convert_params = cs.signal('convert_params')

circ_apis = cs.signal('circ_apis')

record_actions = cs.signal('record_actions')
