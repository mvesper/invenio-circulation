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
