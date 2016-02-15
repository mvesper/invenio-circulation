"""View blueprints for circulation."""

from .circulation import blueprint as circulation_blueprint
from .lists import blueprint as lists_blueprint 
from .entity import blueprint as entity_blueprint
from .user import blueprint as user_blueprint

blueprints = [
    circulation_blueprint,
    lists_blueprint,
    entity_blueprint,
    user_blueprint
]
