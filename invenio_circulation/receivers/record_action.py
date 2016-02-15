from invenio_circulation.signals import record_actions


def _record_actions(sender, data):
    from flask import render_template
    from invenio_circulation.models import CirculationItem

    res = None
    if CirculationItem.search('record_id:{0}'.format(data['record_id'])):
        res = render_template('search/library_copies.html', **data)

    return {'name': 'circulation', 'result': res}


record_actions.connect(_record_actions)
