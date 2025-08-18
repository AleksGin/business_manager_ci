from calendars.schemas import (
    CalendarDay,
    CalendarFilter,
    CalendarMonth,
    CalendarStats,
    CalendarUpcoming,
    CalendarWeek,
)
from calendars.services import CalendarService
from datetime import datetime
from typing import Optional
from uuid import UUID

from meetings.interfaces import MeetingRepository
from tasks.interfaces import TaskRepository
from users.interfaces import UserRepository


class GetCalendarMonthInteractor:
    """Интерактор для получения календаря на месяц"""

    def __init__(
        self,
        task_repo: TaskRepository,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
    ) -> None:
        self._calendar_service = CalendarService(
            task_repo=task_repo,
            meeting_repo=meeting_repo,
            user_repo=user_repo,
        )

    async def __call__(
        self,
        actor_uuid: UUID,
        year: int,
        month: int,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarMonth:
        """Получить календарь на месяц"""
        return await self._calendar_service.get_calendar_month(
            actor_uuid=actor_uuid,
            year=year,
            month=month,
            calendar_filter=calendar_filter,
        )


class GetCalendarWeekInteractor:
    """Интерактор для получения календаря на неделю"""

    def __init__(
        self,
        task_repo: TaskRepository,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
    ) -> None:
        self._calendar_service = CalendarService(
            task_repo=task_repo,
            meeting_repo=meeting_repo,
            user_repo=user_repo,
        )

    async def __call__(
        self,
        actor_uuid: UUID,
        date: datetime,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarWeek:
        """Получить календарь на неделю"""
        return await self._calendar_service.get_calendar_week(
            actor_uuid=actor_uuid,
            date=date,
            calendar_filter=calendar_filter,
        )


class GetCalendarDayInteractor:
    """Интерактор для получения календаря на день"""

    def __init__(
        self,
        task_repo: TaskRepository,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
    ) -> None:
        self._calendar_service = CalendarService(
            task_repo=task_repo,
            meeting_repo=meeting_repo,
            user_repo=user_repo,
        )

    async def __call__(
        self,
        actor_uuid: UUID,
        date: datetime,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarDay:
        """Получить календарь на день"""
        return await self._calendar_service.get_calendar_day(
            actor_uuid=actor_uuid,
            date=date,
            calendar_filter=calendar_filter,
        )


class GetUpcomingEventsInteractor:
    """Интерактор для получения предстоящих событий"""

    def __init__(
        self,
        task_repo: TaskRepository,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
    ) -> None:
        self._calendar_service = CalendarService(
            task_repo=task_repo,
            meeting_repo=meeting_repo,
            user_repo=user_repo,
        )

    async def __call__(
        self,
        actor_uuid: UUID,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarUpcoming:
        """Получить предстоящие события"""
        return await self._calendar_service.get_upcoming_events(
            actor_uuid=actor_uuid,
            calendar_filter=calendar_filter,
        )


class GetCalendarStatsInteractor:
    """Интерактор для получения статистики календаря"""

    def __init__(
        self,
        task_repo: TaskRepository,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
    ) -> None:
        self._calendar_service = CalendarService(
            task_repo=task_repo,
            meeting_repo=meeting_repo,
            user_repo=user_repo,
        )

    async def __call__(
        self,
        actor_uuid: UUID,
        start_date: datetime,
        end_date: datetime,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarStats:
        """Получить статистику календаря за период"""
        return await self._calendar_service.get_calendar_stats(
            actor_uuid=actor_uuid,
            start_date=start_date,
            end_date=end_date,
            calendar_filter=calendar_filter,
        )
