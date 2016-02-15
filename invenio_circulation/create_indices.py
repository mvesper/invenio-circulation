from invenio_circulation.models import entities

for name, _, cls in filter(lambda x: x[0] != 'Record', entities):
    mapping = mappings.get(name, {})
    index = cls.__tablename__
    cls._es.indices.delete(index=index, ignore=404)
    cls._es.indices.create(index=index, body=mapping)
