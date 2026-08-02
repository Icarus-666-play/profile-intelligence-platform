"""Migration base types."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.engine import Connection


class Migration(ABC):
    """A single, versioned schema migration.

    Subclasses must set ``version`` (sortable string, e.g. ``001``) and
    ``name``, and implement :meth:`up`.
    """

    version: str
    name: str

    @abstractmethod
    def up(self, connection: Connection) -> None:
        """Apply the migration."""

    def down(self, connection: Connection) -> None:
        """Optionally reverse the migration (not required for forward-only)."""
        raise NotImplementedError(
            f"Migration {self.version}_{self.name} does not support downgrade"
        )
