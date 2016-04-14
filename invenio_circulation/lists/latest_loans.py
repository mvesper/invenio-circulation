import datetime

from flask import render_template


class LatestLoans(object):
    @classmethod
    def entrance(cls):
        end_date = datetime.date.today()
        start_date = datetime.date.today() - datetime.timedelta(weeks=1)

        return render_template('lists/latest_loans_entrance.html',
                               active_nav='lists',
                               link='latest_loans',
                               start_date=start_date, end_date=end_date)

    @classmethod
    def detail(cls, start_date, end_date):
        from invenio_circulation.models import CirculationLoanCycle

        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

        def check(clc):
            return start_date <= clc.start_date <= end_date

        clcs = [x for x in CirculationLoanCycle.get_all() if check(x)]

        return render_template('lists/latest_loans_detail.html',
                               active_nav='lists', clcs=clcs,
                               link='latest_loans',
                               start_date=start_date, end_date=end_date)
        '''
        from invenio_db import db
        from invenio_circulation.models import CirculationLoanCycle as CLC

        latest_ids = (db.session.query(CLC.id)
                      .filter(db.and_(CLC.creation_date >= start_date,
                                      CLC.creation_date <= end_date))
                      .distinct())
        clcs = [CLC.get(x[0]) for x in latest_ids]

        return render_template('lists/latest_loans_detail.html',
                               active_nav='lists', clcs=clcs,
                               link='latest_loans',
                               start_date=start_date, end_date=end_date)
        '''
