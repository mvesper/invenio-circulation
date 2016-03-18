import invenio_circulation.models as models

from invenio_circulation.api.event import create as create_event
from invenio_circulation.api.utils import update as _update


def create(template_name, subject, header, content):
    cmt = models.CirculationMailTemplate.new(
            template_name=template_name, subject=subject, header=header,
            content=content)

    create_event(mail_template_id=cmt.id,
                 event=models.CirculationMailTemplate.EVENT_CREATE)

    return cmt


def update(cmt, **kwargs):
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
    create_event(mail_template_id=cmt.id,
                 event=models.CirculationMailTemplate.EVENT_DELETE)
    cmt.delete()


schema = {}
