import enum as PyEnum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.models.base import Base

if TYPE_CHECKING:
    from users.models import User


class TokenType(PyEnum.Enum):
    """Типы токенов"""

    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class UserToken(Base):
    """Модель для хранения пользовательских токенов"""

    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    token_type: Mapped[TokenType] = mapped_column(
        Enum(TokenType),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[str] = mapped_column(
        String(500),
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="tokens",
        lazy="select",
    )

    def is_expired(self) -> bool:
        """Проверить истек ли токен"""
        return datetime.now() >= self.expires_at

    def is_valid(self) -> bool:
        """Проверить валиден ли токен (активен или не истек)"""
        return self.is_active and not self.is_expired()

    def __repr__(self) -> str:
        return (
            f"<UserToken(user_uuid={self.user_uuid}, "
            f"type={self.token_type.value}, "
            f"expires_at={self.expires_at}, "
            f"is_active={self.is_active})>"
        )
