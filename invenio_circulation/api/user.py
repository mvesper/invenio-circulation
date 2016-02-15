from invenio_circulation.models import (CirculationUser,
                                                CirculationEvent)
from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(invenio_user_id, ccid, name, address, mailbox, email, phone,
           notes, user_group):
    cu = CirculationUser.new(invenio_user_id=invenio_user_id, ccid=ccid,
                             name=name, address=address,
                             mailbox=mailbox, email=email, phone=phone,
                             notes=notes, user_group=user_group)

    create_event(user_id=cu.id, event=CirculationEvent.EVENT_USER_CREATE)

    return cu


def update(cu, **kwargs):
    current_items, changed = _update(cu, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(user_id=cu.id, event=CirculationEvent.EVENT_USER_CHANGE,
                     description=', '.join(changes_str))


def delete(cu):
    create_event(user_id=cu.id, event=CirculationEvent.EVENT_USER_DELETE)
    cu.delete()


schema = {}
