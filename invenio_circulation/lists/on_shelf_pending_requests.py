from flask import render_template


class OnShelfPendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import (CirculationItem,
                                                        CirculationLoanCycle)
        query = 'current_status:{0}'.format(CirculationItem.STATUS_ON_SHELF)
        status_req = CirculationLoanCycle.STATUS_REQUESTED

        res = []
        for item in CirculationItem.search(query):
            query1 = 'current_status:{0} item_id:{1}'.format(status_req,
                                                             item.id)
            if CirculationLoanCycle.search(query1):
                res.append(item)

        return render_template('lists/display_items.html',
                               active_nav='lists', items=res)

    @classmethod
    def detail(cls, query):
        pass
