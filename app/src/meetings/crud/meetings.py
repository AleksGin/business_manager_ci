from datetime import (
    datetime,
    timedelta,
)
from typing import (
    List,
    Optional,
)
from uuid import UUID

from sqlalchemy import (
    and_,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models.associations import meeting_participants
from src.meetings.interfaces import MeetingRepository
from src.meetings.models import Meeting
from src.users.models import User


class MeetingCRUD(MeetingRepository):
    """Имплементация MeetingRepository"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_meeting(self, meeting: Meeting) -> Meeting:
        """Создать новую встречу"""
        self._session.add(meeting)
        await self._session.flush()
        await self._session.refresh(meeting)
        return meeting

    async def get_by_uuid(self, meeting_uuid: UUID) -> Optional[Meeting]:
        """Получить встречу по UUID"""
        stmt = select(Meeting).where(Meeting.uuid == meeting_uuid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_meeting(self, meeting: Meeting) -> Meeting:
        """Обновить встречу"""
        await self._session.flush()
        await self._session.refresh(meeting)
        return meeting

    async def delete_meeting(self, meeting_uuid: UUID) -> bool:
        """Удалить встречу"""
        meeting = await self.get_by_uuid(meeting_uuid)

        if not meeting:
            return False

        await self._session.delete(meeting)
        await self._session.flush()
        return True

    async def get_meeting_with_participants(
        self, meeting_uuid: UUID
    ) -> Optional[Meeting]:
        """Получить встречу с загруженными участниками"""
        stmt = select(Meeting).where(Meeting.uuid == meeting_uuid)
        stmt = stmt.options(
            selectinload(Meeting.participants),  # Загружаем участников
            selectinload(Meeting.creator),  # Загружаем создателя
            selectinload(Meeting.team),  # Загружаем команду
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

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
        stmt = select(Meeting)

        # Применяем фильтры
        conditions = []

        if team_uuid is not None:
            conditions.append(Meeting.team_uuid == team_uuid)

        if creator_uuid is not None:
            conditions.append(Meeting.creator_uuid == creator_uuid)

        if participant_uuid is not None:
            # Соединение через таблицу many-to-many
            stmt = stmt.join(meeting_participants)
            stmt = stmt.join(User)
            conditions.append(User.uuid == participant_uuid)

        if date_from is not None:
            conditions.append(Meeting.date_time >= date_from)

        if date_to is not None:
            conditions.append(Meeting.date_time <= date_to)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Пагинация и сортировка
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(Meeting.date_time.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_meetings(
        self,
        user_uuid: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Meeting]:
        """Получить встречи пользователя (созданные или участвует)"""
        # Подзапрос для встреч, где пользователь участник
        participant_subquery = select(meeting_participants.c.meeting_uuid).where(
            meeting_participants.c.user_uuid == user_uuid
        )

        conditions = [
            or_(
                Meeting.creator_uuid == user_uuid,
                Meeting.uuid.in_(participant_subquery),
            )
        ]

        if date_from is not None:
            conditions.append(Meeting.date_time >= date_from)

        if date_to is not None:
            conditions.append(Meeting.date_time <= date_to)

        stmt = select(Meeting).where(and_(*conditions))
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(Meeting.date_time.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_meetings(
        self,
        team_uuid: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Meeting]:
        """Получить встречи команды"""
        conditions = [Meeting.team_uuid == team_uuid]

        if date_from is not None:
            conditions.append(Meeting.date_time >= date_from)

        if date_to is not None:
            conditions.append(Meeting.date_time <= date_to)

        stmt = select(Meeting).where(and_(*conditions))
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(Meeting.date_time.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_upcoming_meetings(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Meeting]:
        """Получить предстоящие встречи"""
        now = datetime.now()
        conditions = [Meeting.date_time > now]

        if user_uuid is not None:
            # Встречи где пользователь создатель или участник
            participant_subquery = select(meeting_participants.c.meeting_uuid).where(
                meeting_participants.c.user_uuid == user_uuid
            )
            conditions.append(
                or_(
                    Meeting.creator_uuid == user_uuid,
                    Meeting.uuid.in_(participant_subquery),
                )
            )

        if team_uuid is not None:
            conditions.append(Meeting.team_uuid == team_uuid)

        stmt = select(Meeting).where(and_(*conditions))
        stmt = stmt.limit(limit)
        stmt = stmt.order_by(Meeting.date_time.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_meetings_by_date(
        self,
        target_date: datetime,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
    ) -> List[Meeting]:
        """Получить встречи на конкретную дату"""
        # Начало и конец дня
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        conditions = [
            Meeting.date_time >= start_of_day,
            Meeting.date_time < end_of_day,
        ]

        if user_uuid is not None:
            participant_subquery = select(meeting_participants.c.meeting_uuid).where(
                meeting_participants.c.user_uuid == user_uuid
            )
            conditions.append(
                or_(
                    Meeting.creator_uuid == user_uuid,
                    Meeting.uuid.in_(participant_subquery),
                )
            )

        if team_uuid is not None:
            conditions.append(Meeting.team_uuid == team_uuid)

        stmt = select(Meeting).where(and_(*conditions))
        stmt = stmt.order_by(Meeting.date_time.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def check_time_conflicts(
        self,
        user_uuid: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_meeting_uuid: Optional[UUID] = None,
    ) -> List[Meeting]:
        """Проверить конфликты времени для пользователя"""
        # Встречи где пользователь создатель или участник
        participant_subquery = select(meeting_participants.c.meeting_uuid).where(
            meeting_participants.c.user_uuid == user_uuid
        )

        conditions = [
            or_(
                Meeting.creator_uuid == user_uuid,
                Meeting.uuid.in_(participant_subquery),
            ),
            # Пересечение времени
            Meeting.date_time < end_time,
            # Предполагаем, что встреча длится 1 час по умолчанию
            (Meeting.date_time + timedelta(hours=1)) > start_time,
        ]

        if exclude_meeting_uuid:
            conditions.append(Meeting.uuid != exclude_meeting_uuid)

        stmt = select(Meeting).where(and_(*conditions))
        stmt = stmt.order_by(Meeting.date_time.asc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_participant(
        self,
        meeting_uuid: UUID,
        user_uuid: UUID,
    ) -> bool:
        """Добавить участника во встречу"""
        # Проверяем, не является ли уже участником
        if await self.is_participant(meeting_uuid, user_uuid):
            return False  # Уже участник

        # Добавляем в таблицу many-to-many
        stmt = meeting_participants.insert().values(
            meeting_uuid=meeting_uuid,
            user_uuid=user_uuid,
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return True

    async def remove_participant(
        self,
        meeting_uuid: UUID,
        user_uuid: UUID,
    ) -> bool:
        """Удалить участника из встречи"""
        stmt = meeting_participants.delete().where(
            and_(
                meeting_participants.c.meeting_uuid == meeting_uuid,
                meeting_participants.c.user_uuid == user_uuid,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def is_participant(
        self,
        meeting_uuid: UUID,
        user_uuid: UUID,
    ) -> bool:
        """Проверить является ли пользователь участником встречи"""
        stmt = select(meeting_participants).where(
            and_(
                meeting_participants.c.meeting_uuid == meeting_uuid,
                meeting_participants.c.user_uuid == user_uuid,
            )
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def count_meetings_by_period(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        days: int = 30,
    ) -> int:
        """Подсчитать количество встреч за период"""
        since_date = datetime.now() - timedelta(days=days)

        conditions = [Meeting.date_time >= since_date]

        if user_uuid is not None:
            participant_subquery = select(meeting_participants.c.meeting_uuid).where(
                meeting_participants.c.user_uuid == user_uuid
            )
            conditions.append(
                or_(
                    Meeting.creator_uuid == user_uuid,
                    Meeting.uuid.in_(participant_subquery),
                )
            )

        if team_uuid is not None:
            conditions.append(Meeting.team_uuid == team_uuid)

        stmt = select(func.count(Meeting.uuid)).where(and_(*conditions))
        result = await self._session.execute(stmt)
        return result.scalar() or 0
