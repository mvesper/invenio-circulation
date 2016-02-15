from invenio_circulation.signals import user_current_holds


def _user_current_holds(sender, data):
    import json
    import invenio_circulation.models as models

    from flask import render_template, request, flash
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


user_current_holds.connect(_user_current_holds)
