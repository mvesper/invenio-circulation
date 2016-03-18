from flask import render_template


class OverduePendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import CirculationLoanCycle

        status_over = CirculationLoanCycle.STATUS_OVERDUE
        q1 = 'additional_statuses:{0}'.format(status_over)
        q2 = 'current_status:{0}'.format(CirculationLoanCycle.STATUS_REQUESTED)

        over_clcs = CirculationLoanCycle.search(q1)
        req_clcs = set(x.item.id for x in CirculationLoanCycle.search(q2))

        res = [clc for clc in over_clcs if clc.item.id in req_clcs]

        return render_template('lists/overdue_items.html',
                               active_nav='lists', clcs=res)

    @classmethod
    def detail(cls, query):
        pass
