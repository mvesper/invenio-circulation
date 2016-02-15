from invenio_circulation.signals import (try_action,
                                                 run_action,
                                                 convert_params,
                                                 circ_apis)


def _get_action(action, try_action=False):
    import invenio_circulation.api as api

    actions = {'loan': (api.circulation, 'loan_items'),
               'request': (api.circulation, 'request_items'),
               'return': (api.circulation, 'return_items'),
               'cancel_clcs': (api.loan_cycle, 'cancel_clcs'),
               'loan_extension': (api.loan_cycle, 'loan_extension'),
               'lose_items': (api.item, 'lose_items')}

    try_action = 'try_' if try_action else ''

    _api, func_name = actions[action]

    return getattr(_api, try_action + func_name)


def _try_action(action, data):
    from invenio_circulation.api.utils import ValidationExceptions
    from invenio_circulation.views.utils import filter_params

    try:
        filter_params(_get_action(action, True), **data)
        res = True
    except KeyError:
        res = None
    except ValidationExceptions as e:
        res = [(ex[0], str(ex[1])) for ex in e.exceptions]

    return {'name': 'circulation', 'result': res}


def _run_action(action, data):
    from invenio_circulation.views.utils import filter_params

    try:
        filter_params(_get_action(action), **data)
        res = _get_message(action, data)
    except KeyError:
        res = None

    return {'name': 'circulation', 'result': res}


def _convert_params(action, data):
    import datetime
    import invenio_circulation.models as models

    try:
        user = models.CirculationUser.get(data['users'][0])
    except Exception:
        user = None

    try:
        items = [models.CirculationItem.get(x) for x in data['items']]
    except Exception:
        items = None

    if not items:
        try:
            items = [models.CirculationItem.get(data['item_id'])]
        except Exception:
            items = None

    try:
        clcs = [models.CirculationLoanCycle.get(x) for x in data['clcs']]
    except Exception:
        clcs = None

    if not clcs:
        try:
            clcs = [models.CirculationLoanCycle.get(data['clc_id'])]
        except Exception:
            clcs = None

    try:
        start_date = datetime.datetime.strptime(data['start_date'],
                                                "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(data['end_date'],
                                              "%Y-%m-%d").date()
    except Exception:
        start_date, end_date = None, None

    try:
        red = datetime.datetime.strptime(data['requested_end_date'],
                                         "%Y-%m-%d").date()
    except Exception:
        red = None

    res = {'user': user, 'items': items, 'clcs': clcs,
           'start_date': start_date, 'end_date': end_date,
           'requested_end_date': red}

    return {'name': 'circulation', 'result': res}


def _get_message(action, data):
    from flask import render_template

    if action == 'loan':
        barcodes = ','.join(x.barcode for x in data['items'])
        user_id = data['user'].ccid
        return render_template('messages/loan.msg',
                               item_barcodes=barcodes, user_id=user_id)
    elif action == 'request':
        barcodes = ','.join(x.barcode for x in data['items'])
        user_id = data['user'].ccid
        return render_template('messages/request.msg',
                               item_barcodes=barcodes, user_id=user_id)
    elif action == 'return':
        barcodes = ','.join(x.barcode for x in data['items'])
        return render_template('messages/return.msg', item_barcodes=barcodes)
    elif action == 'cancel_clcs':
        barcodes = ','.join(x.item.barcode for x in data['clcs'])
        return render_template('messages/cancel_clc.msg',
                               item_barcodes=barcodes)
    elif action == 'loan_extension':
        barcodes = ','.join(x.barcode for x in data['items'])
        return render_template('messages/loan_extension.msg',
                               item_barcodes=barcodes)
    elif action == 'lose_items':
        barcodes = ','.join(x.barcode for x in data['items'])
        return render_template('messages/lose_items.msg',
                               item_barcodes=barcodes)
    else:
        return 'success'


def _apis(entity, data):
    import invenio_circulation.api as api

    apis = {'item': api.item, 'loan_cycle': api.loan_cycle, 'user': api.user,
            'event': api.event, 'loan_rule': api.loan_rule,
            'location': api.location, 'mail_template': api.mail_template}

    return {'name': 'circulation', 'result': apis.get(entity)}


try_action.connect(_try_action)
run_action.connect(_run_action)
convert_params.connect(_convert_params)
circ_apis.connect(_apis)
