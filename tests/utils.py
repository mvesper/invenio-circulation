import datetime


def _create_dates(start_days=0, start_weeks=0, end_days=0, end_weeks=4):
    start_date = (datetime.date.today() +
                  datetime.timedelta(days=start_days, weeks=start_weeks))
    end_date = (start_date +
                datetime.timedelta(days=end_days, weeks=end_weeks))
    return start_date, end_date
