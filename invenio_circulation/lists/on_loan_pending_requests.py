from flask import render_template


class OnLoanPendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import CirculationLoanCycle

        q1 = 'current_status:{0}'.format(CirculationLoanCycle.STATUS_ON_LOAN)
        q2 = 'current_status:{0}'.format(CirculationLoanCycle.STATUS_REQUESTED)

        loan_clcs = CirculationLoanCycle.search(q1)
        req_clcs = set(x.item.id for x in CirculationLoanCycle.search(q2))

        res = [clc for clc in loan_clcs if clc.item.id in req_clcs]

        return render_template('lists/on_loan_pending_requests.html',
                               active_nav='lists', clcs=res)

    @classmethod
    def detail(cls, query):
        pass
