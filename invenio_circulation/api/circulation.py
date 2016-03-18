import uuid
import datetime

import invenio_circulation.models as models

from invenio_circulation.api.utils import (DateException,
                                           ValidationExceptions,
                                           email_notification,
                                           _check_loan_duration,
                                           _check_loan_period)
from invenio_circulation.api.loan_cycle import update_waitlist
from invenio_circulation.api.event import create as create_event


def _check_user(user):
    if not user:
        raise Exception('A user is required to loan an item.')
    if isinstance(user, (list, tuple)):
        raise Exception('An item can only be loaned to one user.')
    if not isinstance(user, models.CirculationUser):
        raise Exception('The item must be of the type CirculationUser.')


def _check_items(items):
    if not items:
        raise Exception('A item is required to loan an item.')
    if not isinstance(items, (list, tuple)):
        raise Exception('Items must be a list or tuple.')
    if not all(map(lambda x: isinstance(x, models.CirculationItem), items)):
        raise Exception('The items must be of the type CirculationItem.')


def _check_item_status(items, statuses):
    s = ('The item{0} {1} {2} in the wrong status: '
         'current: {3}, required: {4}')

    statuses = statuses if isinstance(statuses, list) else [statuses]

    _barcodes, _statuses = [], []

    for item in items:
        if item.current_status not in statuses:
            _barcodes.append(item.barcode)
            _statuses.append(item.current_status)
    if _barcodes:
        _s = '' if len(_barcodes) == 1 else 's'
        _is = 'is' if len(_barcodes) == 1 else 'are'
        raise Exception(s.format(_s, ', '.join(_barcodes), _is,
                                 ', '.join(_statuses), ' or '.join(statuses)))


def _check_loan_start(start_date):
    if start_date != datetime.date.today():
        raise Exception('For a loan, the start date must be today.')


def _check_request_start(start_date):
    if start_date < datetime.date.today():
        raise Exception('To request, the start date must be today or later.')


def try_loan_items(user, items, start_date, end_date,
                   waitlist=False, delivery=None):

    exceptions = []
    try:
        _check_items(items)
    except Exception as e:
        exceptions.append(('items', e))

    try:
        _check_item_status(items, models.CirculationItem.STATUS_ON_SHELF)
    except Exception as e:
        exceptions.append(('items_status', e))

    try:
        _check_user(user)
    except Exception as e:
        exceptions.append(('user', e))

    try:
        _check_loan_start(start_date)
    except Exception as e:
        exceptions.append(('start_date', e))

    try:
        _check_loan_duration(user, items, start_date, end_date)
    except Exception as e:
        exceptions.append(('duration', e))

    try:
        _check_loan_period(user, items, start_date, end_date)
    except DateException as e:
        exceptions.append(('date_suggestion', e))
    except Exception as e:
        exceptions.append(('date', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


def loan_items(user, items, start_date, end_date,
               waitlist=False, delivery=None):
    try:
        try_loan_items(user, items, start_date, end_date, waitlist)
        desired_start_date = start_date
        desired_end_date = end_date
    except ValidationExceptions as e:
        if [x[0] for x in e.exceptions] == ['date_suggestion'] and waitlist:
            _start, _end = e.exceptions[0][1].contained_dates
            desired_start_date = start_date
            desired_end_date = end_date
            start_date = _start
            end_date = _end
            if _start != desired_start_date:
                raise e
        else:
            raise e

    if delivery is None:
        delivery = models.CirculationLoanCycle.DELIVERY_DEFAULT
    group_uuid = str(uuid.uuid4())
    res = []
    for item in items:
        item.current_status = models.CirculationItem.STATUS_ON_LOAN
        item.save()
        current_status = models.CirculationLoanCycle.STATUS_ON_LOAN
        clc = models.CirculationLoanCycle.new(
                current_status=current_status, additional_statuses=[],
                item_id=item.id, item=item, user_id=user.id, user=user,
                start_date=start_date, end_date=end_date,
                desired_start_date=desired_start_date,
                desired_end_date=desired_end_date,
                issued_date=datetime.datetime.now(),
                group_uuid=group_uuid, delivery=delivery)

        res.append(clc)

        create_event(user_id=user.id, item_id=item.id, loan_cycle_id=clc.id,
                     event=models.CirculationLoanCycle.EVENT_CREATED_LOAN)

    email_notification('item_loan', 'john.doe@cern.ch', user.email,
                       name=user.name, action='loaned',
                       items=[x.record.title for x in items])

    return res


def try_request_items(user, items, start_date, end_date,
                      waitlist=False, delivery=None):
    exceptions = []
    try:
        _check_items(items)
    except Exception as e:
        exceptions.append(('items', e))

    try:
        statuses = [models.CirculationItem.STATUS_ON_LOAN,
                    models.CirculationItem.STATUS_ON_SHELF]
        _check_item_status(items, statuses)
    except Exception as e:
        exceptions.append(('items_status', e))

    try:
        _check_user(user)
    except Exception as e:
        exceptions.append(('user', e))

    try:
        _check_request_start(start_date)
    except Exception as e:
        exceptions.append(('start_date', e))

    try:
        _check_loan_duration(user, items, start_date, end_date)
    except Exception as e:
        exceptions.append(('duration', e))

    try:
        _check_loan_period(user, items, start_date, end_date)
    except DateException as e:
        exceptions.append(('date_suggestion', e))
    except Exception as e:
        exceptions.append(('date', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


def request_items(user, items, start_date, end_date,
                  waitlist=False, delivery=None):
    try:
        try_request_items(user, items, start_date, end_date, waitlist)
        desired_start_date = start_date
        desired_end_date = end_date
    except ValidationExceptions as e:
        if [x[0] for x in e.exceptions] == ['date_suggestion'] and waitlist:
            _start, _end = e.exceptions[0][1].contained_dates
            desired_start_date = start_date
            desired_end_date = end_date
            start_date = _start
            end_date = _end
        else:
            raise e

    if delivery is None:
        delivery = models.CirculationLoanCycle.DELIVERY_DEFAULT

    group_uuid = str(uuid.uuid4())
    res = []
    for item in items:
        current_status = models.CirculationLoanCycle.STATUS_REQUESTED
        clc = models.CirculationLoanCycle.new(
                current_status=current_status, item=item, user=user,
                start_date=start_date, end_date=end_date,
                desired_start_date=desired_start_date,
                desired_end_date=desired_end_date,
                issued_date=datetime.datetime.now(),
                group_uuid=group_uuid, delivery=delivery)

        res.append(clc)

        create_event(user_id=user.id, item_id=item.id, loan_cycle_id=clc.id,
                     event=models.CirculationLoanCycle.EVENT_CREATED_REQUEST)

    email_notification('item_loan', 'john.doe@cern.ch', user.email,
                       name=user.name, action='requested',
                       items=[x.record.title for x in items])

    return res


def try_return_items(items):
    exceptions = []
    try:
        _check_items(items)
    except Exception as e:
        exceptions.append(('items', e))

    try:
        _check_item_status(items, models.CirculationItem.STATUS_ON_LOAN)
    except Exception as e:
        exceptions.append(('items_status', e))

    if exceptions:
        raise ValidationExceptions(exceptions)


def return_items(items):
    try:
        try_return_items(items)
    except ValidationExceptions as e:
        raise e

    from invenio_circulation.views.utils import send_signal
    from invenio_circulation.signals import item_returned

    for item in items:
        item.current_status = models.CirculationItem.STATUS_ON_SHELF
        item.save()
        try:
            on_loan = models.CirculationLoanCycle.STATUS_ON_LOAN
            query = 'item_id:{0} current_status:{1}'.format(item.id, on_loan)
            clc = models.CirculationLoanCycle.search(query)[0]
            clc.current_status = models.CirculationLoanCycle.STATUS_FINISHED
            clc.save()
            update_waitlist(clc)
            create_event(user_id=clc.user.id, item_id=item.id,
                         loan_cycle_id=clc.id,
                         event=models.CirculationLoanCycle.EVENT_FINISHED)

            send_signal(item_returned, None, item.id)
        except IndexError:
            # if the above fails, and no one returns on the signal, something
            # went wrong
            if not send_signal(item_returned, None, item.id):
                raise
