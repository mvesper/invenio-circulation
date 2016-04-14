from invenio_circulation.signals import (user_current_holds,
                                         get_circulation_user_info)


def _user_current_holds(sender, data):
    import json
    import invenio_circulation.models as models

    from flask import render_template
    from invenio_circulation.views.utils import (
            _get_cal_heatmap_dates, _get_cal_heatmap_range)

    def make_dict(clc):
        return {'clc': clc,
                'cal_data': json.dumps(_get_cal_heatmap_dates([clc.item])),
                'cal_range': _get_cal_heatmap_range([clc.item])}

    user_id = data
    SL = models.CirculationLoanCycle.STATUS_ON_LOAN
    SR = models.CirculationLoanCycle.STATUS_REQUESTED

    query = 'user_id:{0} current_status:{1}'.format(user_id, SL)
    current_holds = [make_dict(clc) for clc
                     in models.CirculationLoanCycle.search(query)]

    query = 'user_id:{0} current_status:{1}'.format(user_id, SR)
    requested_holds = [make_dict(clc) for clc
                       in models.CirculationLoanCycle.search(query)]

    return {'name': 'user',
            'result': [render_template('user/current_holds.html',
                                       holds=current_holds),
                       render_template('user/requested_holds.html',
                                       holds=requested_holds),
                       render_template('user/user_time_pick_modal.html')]}


def _get_circulation_user_info(sender, data):
    import invenio_circulation.api as api
    from invenio_circulation.models import CirculationUser
    from invenio_circulation.cern_ldap import get_user_info

    # TODO DEBUG
    user_info = get_user_info(nickname=data, email=data, ccid=data)

    invenio_user_id = None
    ccid = user_info['employeeID'][0]
    name = user_info['displayName'][0]
    address = ''
    mailbox = user_info['physicalDeliveryOfficeName'][0]
    division = user_info['division'][0]
    cern_group = user_info['cernGroup'][0]
    email = user_info['mail'][0]
    phone = user_info['telephoneNumber'][0]
    notes = ''
    group = CirculationUser.GROUP_DEFAULT

    user = api.user.create(invenio_user_id, ccid, name, address, mailbox,
                           email, phone, notes, group,
                           division=division, cern_group=cern_group)

    return {'name': 'user', 'result': user}

user_current_holds.connect(_user_current_holds)
get_circulation_user_info.connect(_get_circulation_user_info)
