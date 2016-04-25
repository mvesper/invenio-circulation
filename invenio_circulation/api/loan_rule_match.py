# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""invenio-circulation api for CirculationLoanRuleMatch handling."""

import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(loan_rule_id, item_type, patron_type, location_code, active):
    """Create a CirculationLoanLoanRuleMatch object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    clr = models.CirculationLoanRuleMatch.new(
            loan_rule_id=loan_rule_id, item_type=item_type,
            patron_type=patron_type, location_code=location_code,
            active=active)

    create_event(loan_rule_match_id=clr.id,
                 event=models.CirculationLoanRuleMatch.EVENT_CREATE)

    return clr


def update(clr, **kwargs):
    """Update a CirculationLoanLoanRuleMatch object."""
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
    """Delete a CirculationLoanLoanRuleMatch object."""
    create_event(loan_rule_match_id=clr.id,
                 event=models.CirculationLoanRuleMatch.EVENT_DELETE)
    clr.delete()


schema = {}
