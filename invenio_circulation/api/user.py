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

"""invenio-circulation api responsible for CirculationUser handling."""

import invenio_circulation.models as models

from flask import current_app
from flask_mail import Message
from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(invenio_user_id, ccid, name, address, mailbox, email, phone,
           notes, user_group, division='', cern_group=''):
    """Create a CirculationLoanUser object.

    :raise: ValidationExceptions
    :return: The newly created object.
    """
    cu = models.CirculationUser.new(
            current_status=models.CirculationUser.STATUS_ACTIVE,
            invenio_user_id=invenio_user_id, ccid=ccid, name=name,
            address=address, mailbox=mailbox, email=email, phone=phone,
            notes=notes, user_group=user_group,
            division=division, cern_group=cern_group)

    create_event(user_id=cu.id, event=models.CirculationUser.EVENT_CREATE)

    return cu


def update(cu, **kwargs):
    """Update a CirculationLoanUser object."""
    current_items, changed = _update(cu, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(user_id=cu.id, event=models.CirculationUser.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(cu):
    """Delete a CirculationLoanUser object."""
    create_event(user_id=cu.id, event=models.CirculationUser.EVENT_DELETE)
    cu.delete()


def send_message(users, subject, message):
    """Send a message with the provided subject to the given users."""
    sender = 'john.doe@cern.ch'

    for user in users:
        msg = Message(sender=sender, recipients=[user.email],
                      subject=subject, body=message)

        # TODO: socket exception ~.~
        try:
            current_app.extensions['mail'].send(msg)
        except Exception:
            print msg

        create_event(user_id=user.id,
                     event=models.CirculationUser.EVENT_MESSAGED,
                     description='\n'.join([subject, message]))


schema = {}
