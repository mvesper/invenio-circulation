from invenio_circulation.signals import lists_overview, lists_class


def _lists_overview(sender, data):
    return {'name': 'lists',
            'result': [('Items on loan with pending requests',
                        'on_loan_pending_requests'),
                       ('Items on shelf with pending requests',
                        'on_shelf_pending_requests'),
                       ('Overdue items with pending requests',
                        'overdue_pending_requests'),
                       ('Overdue Items', 'overdue_items'),
                       ('Latest Loans', 'latest_loans')]}


def _lists_class(link, data):
    from invenio_circulation.lists.on_loan_pending_requests import (
            OnLoanPendingRequests)
    from invenio_circulation.lists.on_shelf_pending_requests import (
            OnShelfPendingRequests)
    from invenio_circulation.lists.overdue_pending_requests import (
            OverduePendingRequests)
    from invenio_circulation.lists.overdue_items import OverdueItems
    from invenio_circulation.lists.latest_loans import LatestLoans

    clazzes = {'latest_loans': LatestLoans,
               'overdue_items': OverdueItems,
               'on_shelf_pending_requests': OnShelfPendingRequests,
               'on_loan_pending_requests': OnLoanPendingRequests,
               'overdue_pending_requests': OverduePendingRequests}

    return {'name': 'lists', 'result': clazzes.get(link)}

lists_overview.connect(_lists_overview)
lists_class.connect(_lists_class)
