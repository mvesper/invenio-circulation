from flask import render_template
from collections import OrderedDict


class OnLoanPendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import (CirculationItem,
                                                CirculationLoanCycle)

        query = 'current_status:{0} AND item.current_status:{1}'.format(
                CirculationLoanCycle.STATUS_REQUESTED,
                CirculationItem.STATUS_ON_LOAN)

        clcs = CirculationLoanCycle.search(query)
        return render_template('lists/on_loan_pending_requests.html',
                               active_nav='lists', clcs=clcs)

    @classmethod
    def detail(cls, query):
        pass
