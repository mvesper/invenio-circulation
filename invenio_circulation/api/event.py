from invenio_circulation.models import CirculationEvent


def create(user_id=None, item_id=None, loan_cycle_id=None, location_id=None,
           mail_template_id=None, loan_rule_id=None, loan_rule_match_id=None,
           event=None, description=None, **kwargs):

    ce = CirculationEvent.new(user_id=user_id, item_id=item_id,
                              loan_cycle_id=loan_cycle_id,
                              location_id=location_id,
                              mail_template_id=mail_template_id,
                              loan_rule_id=loan_rule_id,
                              loan_rule_match_id=loan_rule_match_id,
                              event=event, description=description,
                              **kwargs)

    return ce


def update(ce, **kwargs):
    raise Exception('Events are not supposed to be changed.')


def delete(ce):
    raise Exception('Events are not supposed to be deleted.')


schema = {}
