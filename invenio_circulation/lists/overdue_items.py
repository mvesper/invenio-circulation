from flask import render_template


class OverdueItems(object):
    @classmethod
    def entrance(cls):
        from invenio_circulation.models import CirculationLoanCycle

        status = CirculationLoanCycle.STATUS_OVERDUE
        clcs = CirculationLoanCycle.search('additional_statuses:{0}'
                                           .format(status))

        return render_template('lists/overdue_items.html',
                               active_nav='lists', clcs=clcs)

    @classmethod
    def detail(cls, query):
        pass
