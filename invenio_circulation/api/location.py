import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(code, name, notes):
    cl = models.CirculationLocation.new(code=code, name=name, notes=notes)
    create_event(location_id=cl.id,
                 event=models.CirculationLocation.EVENT_CREATE)
    return cl


def update(cl, **kwargs):
    current_items, changed = _update(cl, **kwargs)
    if changed:
        changes_str = ['{0}: {1} -> {2}'.format(key,
                                                current_items[key],
                                                changed[key])
                       for key in changed]
        create_event(location_id=cl.id,
                     event=models.CirculationLocation.EVENT_CHANGE,
                     description=', '.join(changes_str))


def delete(cl):
    create_event(location_id=cl.id,
                 event=models.CirculationLocation.EVENT_DELETE)
    cl.delete()


schema = {}
