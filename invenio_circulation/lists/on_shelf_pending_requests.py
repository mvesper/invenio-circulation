from flask import render_template


class OnShelfPendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import (CirculationItem,
                                                CirculationLoanCycle)

        query = 'current_status:{0} AND item.current_status:{1}'.format(
                CirculationLoanCycle.STATUS_REQUESTED,
                CirculationItem.STATUS_ON_SHELF)

        clcs = CirculationLoanCycle.search(query)
        return render_template('lists/on_shelf_pending_requests.html',
                               active_nav='lists', clcs=clcs)

    @classmethod
    def detail(cls, query):
        pass
