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

"""invenio-circulation api responsible for CirculationMailTemplate handling."""

import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(template_name, subject, header, content):
    """Create a CirculationLoanMailTemplate object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    cmt = models.CirculationMailTemplate.new(
            template_name=template_name, subject=subject, header=header,
            content=content)

    create_event(mail_template_id=cmt.id,
                 event=models.CirculationMailTemplate.EVENT_CREATE)

    return cmt


def update(cmt, **kwargs):
    """Update a CirculationLoanMailTemplate object."""
    current_items, changed = _update(cmt, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(mail_template_id=cmt.id,
                     event=models.CirculationMailTemplate.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(cmt):
    """Delete a CirculationLoanMailTemplate object."""
    create_event(mail_template_id=cmt.id,
                 event=models.CirculationMailTemplate.EVENT_DELETE)
    cmt.delete()


schema = {}
