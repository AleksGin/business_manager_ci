import calendar as python_calendar
from calendars.schemas.calendar import (
    CalendarDay,
    CalendarEvent,
    CalendarFilter,
    CalendarMonth,
    CalendarStats,
    CalendarUpcoming,
    CalendarWeek,
    EventPriority,
    EventType,
)
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    List,
    Optional,
)
from uuid import UUID

from src.meetings.interfaces import MeetingRepository
from src.tasks.interfaces import TaskRepository
from src.tasks.models import StatusEnum
from src.users.interfaces import UserRepository
from src.users.models import RoleEnum


class CalendarService:
    """Сервис для работы с календарем"""

    def __init__(
        self,
        task_repo: TaskRepository,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
    ) -> None:
        self._task_repo = task_repo
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo

    async def get_calendar_month(
        self,
        actor_uuid: UUID,
        year: int,
        month: int,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarMonth:
        """Получить календарь на месяц"""

        # 1. Проверить права доступа
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить границы месяца
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)

        # 3. Применить фильтры с учетом прав
        final_filter = await self._apply_permissions_to_filter(actor, calendar_filter)

        # 4. Получить события месяца
        events = await self._get_events_for_period(
            start_date=month_start,
            end_date=month_end,
            calendar_filter=final_filter,
        )

        # 5. Построить календарную сетку
        weeks = await self._build_month_weeks(year, month, events)

        # 6. Вычислить статистику
        total_events = sum(len(day.events) for week in weeks for day in week.days)
        summary = self._calculate_month_summary(events)

        return CalendarMonth(
            year=year,
            month=month,
            month_name=python_calendar.month_name[month],
            weeks=weeks,
            total_events=total_events,
            summary=summary,
        )

    async def get_calendar_week(
        self,
        actor_uuid: UUID,
        date: datetime,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarWeek:
        """Получить календарь на неделю"""

        # 1. Проверить права доступа
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить границы недели (понедельник - воскресенье)
        week_start = date - timedelta(days=date.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # 3. Применить фильтры
        final_filter = await self._apply_permissions_to_filter(actor, calendar_filter)

        # 4. Получить события недели
        events = await self._get_events_for_period(
            start_date=week_start,
            end_date=week_end,
            calendar_filter=final_filter,
        )

        # 5. Построить дни недели
        days = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_events = [e for e in events if e.date_time.date() == day_date.date()]

            days.append(
                CalendarDay(
                    date=day_date,
                    events=day_events,
                    total_events=len(day_events),
                    has_overdue=any(e.is_overdue for e in day_events),
                    has_urgent=any(
                        e.priority == EventPriority.URGENT for e in day_events
                    ),
                )
            )

        return CalendarWeek(
            week_start=week_start,
            week_end=week_end,
            days=days,
            total_events=sum(len(day.events) for day in days),
        )

    async def get_calendar_day(
        self,
        actor_uuid: UUID,
        date: datetime,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarDay:
        """Получить календарь на день"""

        # 1. Проверить права доступа
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить границы дня
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

        # 3. Применить фильтры
        final_filter = await self._apply_permissions_to_filter(actor, calendar_filter)

        # 4. Получить события дня
        events = await self._get_events_for_period(
            start_date=day_start,
            end_date=day_end,
            calendar_filter=final_filter,
        )

        return CalendarDay(
            date=day_start,
            events=sorted(events, key=lambda e: e.date_time),
            total_events=len(events),
            has_overdue=any(e.is_overdue for e in events),
            has_urgent=any(e.priority == EventPriority.URGENT for e in events),
        )

    async def get_upcoming_events(
        self,
        actor_uuid: UUID,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarUpcoming:
        """Получить предстоящие события"""

        # 1. Проверить права доступа
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить временные периоды
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1) - timedelta(seconds=1)
        tomorrow_start = today_start + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1) - timedelta(seconds=1)

        # Неделя (понедельник - воскресенье)
        week_start = today_start - timedelta(days=today_start.weekday())
        week_end = week_start + timedelta(days=7) - timedelta(seconds=1)
        next_week_start = week_end + timedelta(seconds=1)
        next_week_end = next_week_start + timedelta(days=7) - timedelta(seconds=1)

        # 3. Применить фильтры
        final_filter = await self._apply_permissions_to_filter(
            actor,
            calendar_filter,
        )

        # 4. Получить события по периодам
        today_events = await self._get_events_for_period(
            today_start,
            today_end,
            final_filter,
        )
        tomorrow_events = await self._get_events_for_period(
            tomorrow_start,
            tomorrow_end,
            final_filter,
        )
        week_events = await self._get_events_for_period(
            week_start,
            week_end,
            final_filter,
        )
        next_week_events = await self._get_events_for_period(
            next_week_start,
            next_week_end,
            final_filter,
        )

        # Просроченные события
        overdue_events = [
            e
            for e in await self._get_events_for_period(
                datetime(2020, 1, 1),
                now,
                final_filter,
            )
            if e.is_overdue
        ]

        return CalendarUpcoming(
            today=sorted(today_events, key=lambda e: e.date_time),
            tomorrow=sorted(tomorrow_events, key=lambda e: e.date_time),
            this_week=sorted(week_events, key=lambda e: e.date_time),
            next_week=sorted(next_week_events, key=lambda e: e.date_time),
            overdue=sorted(overdue_events, key=lambda e: e.date_time),
        )

    async def get_calendar_stats(
        self,
        actor_uuid: UUID,
        start_date: datetime,
        end_date: datetime,
        calendar_filter: Optional[CalendarFilter] = None,
    ) -> CalendarStats:
        """Получить статистику календаря за период"""

        # 1. Проверить права доступа
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Применить фильтры
        final_filter = await self._apply_permissions_to_filter(
            actor,
            calendar_filter,
        )

        # 3. Получить события
        events = await self._get_events_for_period(
            start_date,
            end_date,
            final_filter,
        )

        # 4. Вычислить статистику
        events_by_type = {event_type: 0 for event_type in EventType}
        events_by_priority = {priority: 0 for priority in EventPriority}

        for event in events:
            events_by_type[event.event_type] += 1
            events_by_priority[event.priority] += 1

        # Дни с событиями
        busy_days = len(set(e.date_time.date() for e in events))

        return CalendarStats(
            period_start=start_date,
            period_end=end_date,
            total_events=len(events),
            events_by_type=events_by_type,
            events_by_priority=events_by_priority,
            overdue_count=sum(1 for e in events if e.is_overdue),
            completed_tasks=sum(
                1 for e in events if e.event_type == EventType.TASK and e.is_completed
            ),
            upcoming_meetings=sum(
                1
                for e in events
                if e.event_type == EventType.MEETING and e.date_time > datetime.now()
            ),
            busy_days=busy_days,
        )

    async def _get_events_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_filter: Optional[CalendarFilter],
    ) -> List[CalendarEvent]:
        """Получить все события за период"""

        events = []

        # Фильтры из CalendarFilter
        team_uuid = calendar_filter.team_uuid if calendar_filter else None
        user_uuid = calendar_filter.user_uuid if calendar_filter else None
        event_types = calendar_filter.event_types if calendar_filter else None
        include_completed = (
            calendar_filter.include_completed if calendar_filter else True
        )

        # Получить задачи
        if (
            not event_types
            or EventType.TASK in event_types
            or EventType.TASK_DEADLINE in event_types
        ):
            tasks = await self._task_repo.list_tasks(
                limit=1000,  # Большой лимит
                team_uuid=team_uuid,
                assignee_uuid=user_uuid,
            )

            for task in tasks:
                # Фильтр по завершенности
                if not include_completed and task.status == StatusEnum.DONE:
                    continue

                # Проверяем попадание дедлайна в период
                if start_date <= task.deadline <= end_date:
                    events.append(self._task_to_calendar_event(task))

        # Получить встречи
        if not event_types or EventType.MEETING in event_types:
            meetings = await self._meeting_repo.list_meetings(
                limit=1000,  # Большой лимит
                team_uuid=team_uuid,
                participant_uuid=user_uuid,
                date_from=start_date,
                date_to=end_date,
            )

            for meeting in meetings:
                events.append(self._meeting_to_calendar_event(meeting))

        return events

    def _task_to_calendar_event(self, task) -> CalendarEvent:
        """Преобразовать задачу в календарное событие"""

        # Определить приоритет по статусу и времени
        now = datetime.now()
        is_overdue = task.deadline < now and task.status != StatusEnum.DONE

        if is_overdue:
            priority = EventPriority.URGENT
        elif task.deadline < now + timedelta(days=1):
            priority = EventPriority.HIGH
        elif task.deadline < now + timedelta(days=7):
            priority = EventPriority.MEDIUM
        else:
            priority = EventPriority.LOW

        return CalendarEvent(
            uuid=task.uuid,
            title=f"📋 {task.title}",
            description=task.description,
            event_type=EventType.TASK_DEADLINE,
            date_time=task.deadline,
            priority=priority,
            team_uuid=task.team_uuid,
            creator_uuid=task.creator_uuid,
            assignee_uuid=task.assignee_uuid,
            is_completed=task.status == StatusEnum.DONE,
            is_overdue=is_overdue,
        )

    def _meeting_to_calendar_event(self, meeting) -> CalendarEvent:
        """Преобразовать встречу в календарное событие"""

        # Определить приоритет по времени
        now = datetime.now()

        if meeting.date_time < now + timedelta(hours=2):
            priority = EventPriority.HIGH
        elif meeting.date_time < now + timedelta(days=1):
            priority = EventPriority.MEDIUM
        else:
            priority = EventPriority.LOW

        return CalendarEvent(
            uuid=meeting.uuid,
            title=f"🤝 {meeting.title}",
            description=meeting.description,
            event_type=EventType.MEETING,
            date_time=meeting.date_time,
            priority=priority,
            team_uuid=meeting.team_uuid,
            creator_uuid=meeting.creator_uuid,
            is_completed=meeting.date_time
            < now,  # Прошедшие встречи считаем завершенными
            is_overdue=False,  # Встречи не могут быть просроченными
        )

    async def _apply_permissions_to_filter(
        self,
        actor,
        calendar_filter: Optional[CalendarFilter],
    ) -> CalendarFilter:
        """Применить права доступа к фильтру"""

        if not calendar_filter:
            calendar_filter = CalendarFilter(
                team_uuid=None,
                user_uuid=None,
                event_types=None,
                include_completed=True,
                include_overdue=True,
                priority_filter=None,
            )

        # Сотрудники видят только события своей команды
        if actor.role == RoleEnum.EMPLOYEE:
            calendar_filter.team_uuid = actor.team_uuid

            # Если указан пользователь, это может быть только сам сотрудник
            if calendar_filter.user_uuid and calendar_filter.user_uuid != actor.uuid:
                raise PermissionError(
                    "Нет прав для просмотра календаря другого пользователя"
                )

        return calendar_filter

    async def _build_month_weeks(
        self,
        year: int,
        month: int,
        events: List[CalendarEvent],
    ) -> List[CalendarWeek]:
        """Построить недели месяца"""

        weeks = []

        # Получить календарную сетку месяца
        cal = python_calendar.monthcalendar(year, month)

        for week_days in cal:
            days = []
            week_start = None

            for day_num in week_days:
                if day_num == 0:
                    # Дни из других месяцев - пропускаем
                    continue

                day_date = datetime(year, month, day_num)

                # Устанавливаем week_start для первого валидного дня недели
                if week_start is None:
                    # Находим понедельник этой недели
                    week_start = day_date - timedelta(days=day_date.weekday())

                # События этого дня
                day_events = [
                    e for e in events if e.date_time.date() == day_date.date()
                ]

                days.append(
                    CalendarDay(
                        date=day_date,
                        events=sorted(day_events, key=lambda e: e.date_time),
                        total_events=len(day_events),
                        has_overdue=any(e.is_overdue for e in day_events),
                        has_urgent=any(
                            e.priority == EventPriority.URGENT for e in day_events
                        ),
                    )
                )

            # Создаем неделю только если есть дни И week_start определен
            if days and week_start is not None:
                week_end = week_start + timedelta(
                    days=6, hours=23, minutes=59, seconds=59
                )
                weeks.append(
                    CalendarWeek(
                        week_start=week_start,
                        week_end=week_end,
                        days=days,
                        total_events=sum(len(day.events) for day in days),
                    )
                )

        return weeks

    def _calculate_month_summary(self, events: List[CalendarEvent]) -> dict:
        """Вычислить сводку месяца"""

        total_tasks = sum(
            1
            for e in events
            if e.event_type in [EventType.TASK, EventType.TASK_DEADLINE]
        )
        total_meetings = sum(1 for e in events if e.event_type == EventType.MEETING)
        completed_tasks = sum(
            1
            for e in events
            if e.event_type in [EventType.TASK, EventType.TASK_DEADLINE]
            and e.is_completed
        )
        overdue_count = sum(1 for e in events if e.is_overdue)

        return {
            "total_tasks": total_tasks,
            "total_meetings": total_meetings,
            "completed_tasks": completed_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100)
            if total_tasks > 0
            else 0,
            "overdue_count": overdue_count,
            "busy_days": len(set(e.date_time.date() for e in events)),
        }
