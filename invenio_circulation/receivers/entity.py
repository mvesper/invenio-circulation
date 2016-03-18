from invenio_circulation.signals import (entities_overview,
                                         entities_hub_search,
                                         entity,
                                         entity_suggestions,
                                         entity_aggregations,
                                         entity_class,
                                         entity_name)


def _entities_overview(sender, data):
    return {'name': 'entity',
            'result': [('Record', 'record'),
                       ('User', 'user'),
                       ('Item', 'item'),
                       ('Loan Cycle', 'loan_cycle'),
                       ('Location', 'location'),
                       ('Event', 'event'),
                       ('Mail Template', 'mail_template'),
                       ('Loan Rule', 'loan_rule'),
                       ('Loan Rule Match', 'loan_rule_match')]}


def _entities_hub_search(sender, data):
    import invenio_circulation.models as models

    search = data

    models_entities = {'record':  models.CirculationRecord,
                       'user': models.CirculationUser,
                       'item': models.CirculationItem,
                       'loan_cycle': models.CirculationLoanCycle,
                       'location': models.CirculationLocation,
                       'event': models.CirculationEvent,
                       'mail_template': models.CirculationMailTemplate,
                       'loan_rule': models.CirculationLoanRule,
                       'loan_rule_match': models.CirculationLoanRuleMatch}

    entity = models_entities.get(sender)
    res = None
    if entity:
        res = (entity.search(search), 'entities/' + sender + '.html')

    return {'name': 'entity', 'result': res}


def _entity(sender, data):
    import invenio_circulation.models as models

    id = data

    models_entities = {'record':  models.CirculationRecord,
                       'user': models.CirculationUser,
                       'item': models.CirculationItem,
                       'loan_cycle': models.CirculationLoanCycle,
                       'location': models.CirculationLocation,
                       'event': models.CirculationEvent,
                       'mail_template': models.CirculationMailTemplate,
                       'loan_rule': models.CirculationLoanRule,
                       'loan_rule_match': models.CirculationLoanRuleMatch}

    entity = models_entities.get(sender)
    res = entity.get(id) if entity else None

    return {'name': 'entity', 'result': res}


def _entity_suggestions(entity, data):
    suggestions = {'item': [('location_id', 'location',
                             ['id', 'code', 'name'],
                             '/circulation/api/entity/search')],
                   'loan_cycle': [('item_id', 'item',
                                   ['id', 'record.title'],
                                   '/circulation/api/entity/search'),
                                  ('user_id', 'user',
                                   ['id', 'name'],
                                   '/circulation/api/entity/search')],
                   'event': [('item_id', 'item',
                              ['id', 'record.title'],
                              '/circulation/api/entity/search'),
                             ('user_id', 'user',
                              ['id', 'name'],
                              '/circulation/api/entity/search'),
                             ('loan_cycle_id', 'loan_cycle',
                              ['id'],
                              '/circulation/api/entity/search'),
                             ('loan_rule_id', 'loan_rule',
                              ['id'],
                              '/circulation/api/entity/search'),
                             ('loan_rule_match_id', 'loan_rule_match',
                              ['id'],
                              '/circulation/api/entity/search'),
                             ('location_id', 'location',
                              ['id', 'code', 'name'],
                              '/circulation/api/entity/search'),
                             ('mail_template_id', 'mail_template',
                              ['id', 'template_name'],
                              '/circulation/api/entity/search'),
                             ]}

    return {'name': 'entity', 'result': suggestions.get(entity)}


def _entity_aggregations(entity, data):
    id = data

    res = None
    if entity == 'record':
        res = _get_record_aggregations(id)
    elif entity == 'item':
        res = _get_item_aggregations(id)
    elif entity == 'user':
        res = _get_user_aggregations(id)
    elif entity == 'loan_cycle':
        res = _get_loan_cycle_aggregations(id)
    elif entity == 'location':
        res = _get_location_aggregations(id)
    elif entity == 'event':
        res = _get_event_aggregations(id)

    return {'name': 'entity', 'result': res}


def _get_event_aggregations(id):
    import invenio_circulation.models as models

    from flask import render_template

    def _get(entity, event):
        m = {'record': models.CirculationRecord,
             'user': models.CirculationUser,
             'item': models.CirculationItem,
             'loan_cycle': models.CirculationLoanCycle,
             'location': models.CirculationLocation,
             'event': models.CirculationEvent,
             'mail_template': models.CirculationMailTemplate,
             'loan_rule': models.CirculationLoanRule,
             'loan_rule_match': models.CirculationLoanRuleMatch}

        try:
            return [m[entity].get(event.__getattribute__(entity + '_id'))]
        except TypeError:
            return []

    event = models.CirculationEvent.get(id)

    users = _get('user', event)
    items = _get('item', event)
    clcs = _get('loan_cycle', event)
    locations = _get('location', event)
    mail_templates = _get('mail_template', event)
    loan_rules = _get('loan_rule', event)
    loan_rule_matches = _get('loan_rule_match', event)

    return [render_template('aggregations/user.html', users=users),
            render_template('aggregations/item.html', items=items),
            render_template('aggregations/loan_cycle.html', loan_cycles=clcs),
            render_template('aggregations/location.html', locations=locations),
            render_template('aggregations/mail_template.html',
                            mail_templates=mail_templates),
            render_template('aggregations/loan_rule.html',
                            loan_rules=loan_rules),
            render_template('aggregations/loan_rule_match.html',
                            loan_rule_matches=loan_rule_matches)]


def _get_location_aggregations(id):
    return None


def _get_loan_cycle_aggregations(id):
    import json
    import invenio_circulation.models as models
    import invenio_circulation.api as api

    from flask import render_template
    from invenio_circulation.api.utils import ValidationExceptions
    from invenio_circulation.views.utils import (
            _get_cal_heatmap_dates, _get_cal_heatmap_range)

    def _try(func, item):
        try:
            func([item])
            return True
        except ValidationExceptions:
            return False

    def make_dict(clc):
        return {'clc': clc,
                'cal_data': json.dumps(_get_cal_heatmap_dates([clc.item])),
                'cal_range': _get_cal_heatmap_range([clc.item])}

    clc = models.CirculationLoanCycle.get(id)
    items = [clc.item]
    users = [clc.user]
    events = models.CirculationEvent.search('loan_cycle_id:{0}'.format(id))
    events = sorted(events, key=lambda x: x.creation_date)

    cancel = _try(api.loan_cycle.try_cancel_clcs, clc)
    loan_extension = make_dict(clc)
    overdue = _try(api.loan_cycle.try_overdue_clcs, clc)

    return [render_template('aggregations/loan_cycle_functions.html',
                            cancel=cancel, loan_extension=loan_extension,
                            overdue=overdue),
            render_template('aggregations/user.html', users=users),
            render_template('aggregations/item.html', items=items),
            render_template('aggregations/event.html', events=events),
            render_template('user/user_time_pick_modal.html')]


def _get_user_aggregations(id):
    import invenio_circulation.models as models

    from flask import render_template

    query = 'user_id:{0} AND current_status:{1}'

    q = query.format(id, models.CirculationLoanCycle.STATUS_ON_LOAN)
    l_clcs = models.CirculationLoanCycle.search(q)

    q = query.format(id, models.CirculationLoanCycle.STATUS_REQUESTED)
    r_clcs = models.CirculationLoanCycle.search(q)

    q = query.format(id, models.CirculationLoanCycle.STATUS_FINISHED)
    f_clcs = models.CirculationLoanCycle.search(q)

    return [render_template('aggregations/user_loan_cycles.html',
                            loan_loan_cycles=l_clcs,
                            request_loan_cycles=r_clcs,
                            finished_loan_cycles=f_clcs)]
    '''
    clcs = models.CirculationLoanCycle.search('user_id:{0}'.format(id))
    items = [x.item for x in clcs if x.current_status == 'on_loan']

    return [render_template('aggregations/item.html', items=items),
            render_template('aggregations/loan_cycle.html', loan_cycles=clcs)]
    '''


def _get_record_aggregations(id):
    import invenio_circulation.models as models

    from flask import render_template

    items = models.CirculationItem.search('record_id:{0}'.format(id))
    return [render_template('aggregations/item.html', items=items)]


def _get_item_aggregations(id):
    import invenio_circulation.models as models
    import invenio_circulation.api as api
    from invenio_circulation.api.utils import ValidationExceptions

    from flask import render_template

    def _try(func, item):
        try:
            func([item])
            return True
        except ValidationExceptions:
            return False

    item = models.CirculationItem.get(id)

    record = models.CirculationItem.get(id).record
    clcs = models.CirculationLoanCycle.search('item_id:{0}'.format(id))

    lose = _try(api.item.try_lose_items, item)
    process = _try(api.item.try_process_items, item)
    overdue = _try(api.item.try_overdue_items, item)
    return_missing = _try(api.item.try_return_missing_items, item)

    return [render_template('aggregations/item_functions.html',
                            item=item, lose=lose, process=process,
                            overdue=overdue, return_missing=return_missing),
            render_template('aggregations/record.html', records=[record]),
            render_template('aggregations/loan_cycle.html', loan_cycles=clcs)]


def _entity_class(entity, data):
    import invenio_circulation.models as models

    models = {'record': models.CirculationRecord,
              'user': models.CirculationUser,
              'item': models.CirculationItem,
              'loan_cycle': models.CirculationLoanCycle,
              'location': models.CirculationLocation,
              'event': models.CirculationEvent,
              'mail_template': models.CirculationMailTemplate,
              'loan_rule': models.CirculationLoanRule,
              'loan_rule_match': models.CirculationLoanRuleMatch}

    return {'name': 'entity', 'result': models.get(entity)}


def _entity_name(entity, data):
    names = {'record': 'Record',
             'user': 'User',
             'item': 'Item',
             'loan_cycle': 'Loan Cycle',
             'location': 'Location',
             'event': 'Event',
             'mail_template': 'Mail Template',
             'loan_rule': 'Loan Rule',
             'loan_rule_match': 'Loan Rule Match'}

    return {'name': 'entity', 'result': names.get(entity)}


entities_overview.connect(_entities_overview)
entities_hub_search.connect(_entities_hub_search)
entity.connect(_entity)
entity_suggestions.connect(_entity_suggestions)
entity_aggregations.connect(_entity_aggregations)
entity_class.connect(_entity_class)
entity_name.connect(_entity_name)
