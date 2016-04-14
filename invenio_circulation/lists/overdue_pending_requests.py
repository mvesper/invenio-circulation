from flask import render_template


class OverduePendingRequests(object):
    @classmethod
    def entrance(cls):
        from invenio_db import db
        from invenio_circulation.models import CirculationLoanCycle

        # Get overdue CLC item ids
        over_status = CirculationLoanCycle.STATUS_OVERDUE
        over_ids = (db.session.query(CirculationLoanCycle.item_id)
                    .filter(CirculationLoanCycle.additional_statuses
                            .contains(over_status))
                    .distinct())

        # Get requested CLC with those ids
        req_status = CirculationLoanCycle.STATUS_REQUESTED
        req_ids = (db.session.query(CirculationLoanCycle.id)
                   .filter(db.and_(CirculationLoanCycle.current_status == req_status,
                                   CirculationLoanCycle.item_id.in_(over_ids)))
                   .distinct())
        req_ids = set(x for x in req_ids)

        clcs = [CirculationLoanCycle.get(id[0]) for id in req_ids]

        return render_template('lists/overdue_items.html',
                               active_nav='lists', clcs=clcs)

    @classmethod
    def detail(cls, query):
        pass
