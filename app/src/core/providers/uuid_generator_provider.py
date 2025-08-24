from uuid import (
    UUID,
    uuid4,
)

from src.core.interfaces.common import UUIDGenerator


class UUIDGeneratorProvider(UUIDGenerator):
    """Имплементация UUIDGenerator"""

    def __call__(self) -> UUID:
        """Сгенерировать новый UUID v4"""
        return uuid4()
