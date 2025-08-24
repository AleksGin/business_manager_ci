from datetime import datetime
from typing import (
    List,
    Optional,
    Protocol,
)
from uuid import UUID

from src.meetings.models import Meeting


class MeetingRepository(Protocol):
    """Интерфейс для работы с встречами в хранилище данных"""

    async def create_meeting(self, meeting: Meeting) -> Meeting:
        """Создать новую встречу"""
        ...

    async def get_by_uuid(self, meeting_uuid: UUID) -> Optional[Meeting]:
        """Получить встречу по UUID"""
        ...

    async def update_meeting(self, meeting: Meeting) -> Meeting:
        """Обновить встречу"""
        ...

    async def delete_meeting(self, meeting_uuid: UUID) -> bool:
        """Удалить встречу"""
        ...

    async def get_meeting_with_participants(
        self, meeting_uuid: UUID
    ) -> Optional[Meeting]:
        """Получить встречу с загруженными участниками"""
        ...

    async def list_meetings(
        self,
        limit: int = 50,
        offset: int = 0,
        team_uuid: Optional[UUID] = None,
        creator_uuid: Optional[UUID] = None,
        participant_uuid: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Meeting]:
        """Получить список встреч с фильтрацией"""
        ...

    async def get_user_meetings(
        self,
        user_uuid: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Meeting]:
        """Получить встречи пользователя (созданные или участвует)"""
        ...

    async def get_team_meetings(
        self,
        team_uuid: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Meeting]:
        """Получить встречи команды"""
        ...

    async def get_upcoming_meetings(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Meeting]:
        """Получить предстоящие встречи"""
        ...

    async def get_meetings_by_date(
        self,
        target_date: datetime,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
    ) -> List[Meeting]:
        """Получить встречи на конкретную дату"""
        ...

    async def check_time_conflicts(
        self,
        user_uuid: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_meeting_uuid: Optional[UUID] = None,
    ) -> List[Meeting]:
        """Проверить конфликты времени для пользователя"""
        ...

    async def add_participant(
        self,
        meeting_uuid: UUID,
        user_uuid: UUID,
    ) -> bool:
        """Добавить участника во встречу"""
        ...

    async def remove_participant(
        self,
        meeting_uuid: UUID,
        user_uuid: UUID,
    ) -> bool:
        """Удалить участника из встречи"""
        ...

    async def is_participant(
        self,
        meeting_uuid: UUID,
        user_uuid: UUID,
    ) -> bool:
        """Проверить является ли пользователь участником встречи"""
        ...

    async def count_meetings_by_period(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        days: int = 30,
    ) -> int:
        """Подсчитать количество встреч за период"""
        ...
