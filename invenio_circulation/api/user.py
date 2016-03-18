import invenio_circulation.models as models

from flask import current_app
from flask_mail import Message
from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(invenio_user_id, ccid, name, address, mailbox, email, phone,
           notes, user_group):
    cu = models.CirculationUser.new(
            invenio_user_id=invenio_user_id, ccid=ccid, name=name,
            address=address, mailbox=mailbox, email=email, phone=phone,
            notes=notes, user_group=user_group)

    create_event(user_id=cu.id, event=models.CirculationUser.EVENT_CREATE)

    return cu


def update(cu, **kwargs):
    current_items, changed = _update(cu, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(user_id=cu.id, event=models.CirculationUser.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(cu):
    create_event(user_id=cu.id, event=models.CirculationUser.EVENT_DELETE)
    cu.delete()


def send_message(users, subject, message):
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
