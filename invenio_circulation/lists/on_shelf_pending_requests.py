from flask import render_template


class OnShelfPendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import (CirculationItem,
                                                CirculationLoanCycle)

        q1 = 'current_status:{0}'.format(CirculationItem.STATUS_ON_SHELF)
        q2 = 'current_status:{0}'.format(CirculationLoanCycle.STATUS_REQUESTED)

        shelf_items = set(item.id for item in CirculationItem.search(q1))
        req_clcs = CirculationLoanCycle.search(q2)

        res = [clc for clc in req_clcs if clc.item.id in shelf_items]

        return render_template('lists/on_shelf_pending_requests.html',
                               active_nav='lists', clcs=res)

    @classmethod
    def detail(cls, query):
        pass
