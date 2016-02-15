from flask import render_template


class OverdueItems(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import CirculationLoanCycle
        status = CirculationLoanCycle.STATUS_OVERDUE
        query = 'additional_statuses:{0}'.format(status)

        res = [clc.item for clc in CirculationLoanCycle.search(query)]

        return render_template('lists/display_items.html',
                               active_nav='lists', items=res)

    @classmethod
    def detail(cls, query):
        pass
