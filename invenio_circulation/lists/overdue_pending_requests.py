from flask import render_template


class OverduePendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import (CirculationItem,
                                                        CirculationLoanCycle)

        status = CirculationLoanCycle.STATUS_OVERDUE
        status_req = CirculationLoanCycle.STATUS_REQUESTED
        query = 'additional_statuses:{0}'.format(status)

        res = []
        for item in [clc.item for clc in CirculationLoanCycle.search(query)]:
            query1 = 'current_status:{0} item_id:{1}'.format(status_req,
                                                             item.id)
            if CirculationLoanCycle.search(query1):
                res.append(item)

        return render_template('lists/display_items.html',
                               active_nav='lists', items=res)

    @classmethod
    def detail(cls, query):
        pass
