import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(name, type, loan_period, holdable, home_pickup, renewable,
           automatic_recall):
    clr = models.CirculationLoanRule.new(
            name=name, type=type, loan_period=loan_period,
            holdable=holdable, home_pickup=home_pickup,
            renewable=renewable, automatic_recall=automatic_recall)

    create_event(loan_rule_id=clr.id,
                 event=models.CirculationLoanRule.EVENT_CREATE)

    return clr


def update(clr, **kwargs):
    current_items, changed = _update(clr, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]

        create_event(loan_rule_id=clr.id,
                     event=models.CirculationLoanRule.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(clr):
    create_event(loan_rule_id=clr.id,
                 event=models.CirculationLoanRule.EVENT_DELETE)
    clr.delete()


schema = {}
