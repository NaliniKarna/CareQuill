"""The SQLAlchemy declarative base, isolated in its own module (no other
imports) so model modules can import it without risking a circular import
with app.db.base (which imports every model)."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
