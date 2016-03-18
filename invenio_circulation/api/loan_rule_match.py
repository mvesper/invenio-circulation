import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(loan_rule_id, item_type, patron_type, location_code, active):
    clr = models.CirculationLoanRuleMatch.new(
            loan_rule_id=loan_rule_id, item_type=item_type,
            patron_type=patron_type, location_code=location_code,
            active=active)

    create_event(loan_rule_match_id=clr.id,
                 event=models.CirculationLoanRuleMatch.EVENT_CREATE)

    return clr


def update(clr, **kwargs):
    current_items, changed = _update(clr, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(loan_rule_match_id=clr.id,
                     event=models.CirculationLoanRuleMatch.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(clr):
    create_event(loan_rule_match_id=clr.id,
                 event=models.CirculationLoanRuleMatch.EVENT_DELETE)
    clr.delete()


schema = {}
