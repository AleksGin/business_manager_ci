from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class EventType(str, Enum):
    """Типы событий в календаре"""

    TASK = "task"
    MEETING = "meeting"
    TASK_DEADLINE = "task_deadline"


class EventPriority(str, Enum):
    """Приоритет события"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CalendarEvent(BaseModel):
    """Базовое событие календаря"""

    uuid: UUID
    title: str
    description: Optional[str] = None
    event_type: EventType
    date_time: datetime
    priority: EventPriority = EventPriority.MEDIUM

    # Метаданные
    team_uuid: Optional[UUID] = None
    creator_uuid: Optional[UUID] = None
    assignee_uuid: Optional[UUID] = None  # Для задач

    # Статусы
    is_completed: bool = False  # Для задач
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class CalendarDay(BaseModel):
    """День в календаре"""

    date: datetime = Field(description="Дата (начало дня)")
    events: List[CalendarEvent] = Field(default_factory=list)
    total_events: int = Field(default=0)
    has_overdue: bool = Field(default=False)
    has_urgent: bool = Field(default=False)


class CalendarWeek(BaseModel):
    """Неделя в календаре"""

    week_start: datetime = Field(description="Начало недели (понедельник)")
    week_end: datetime = Field(description="Конец недели (воскресенье)")
    days: List[CalendarDay] = Field(default_factory=list)
    total_events: int = Field(default=0)


class CalendarMonth(BaseModel):
    """Месяц в календаре"""

    year: int
    month: int
    month_name: str
    weeks: List[CalendarWeek] = Field(default_factory=list)
    total_events: int = Field(default=0)
    summary: dict = Field(
        default_factory=dict,
        description="Сводка по месяцу",
    )


class CalendarFilter(BaseModel):
    """Фильтры для календаря"""

    team_uuid: Optional[UUID] = Field(
        None,
        description="UUID команды",
    )
    user_uuid: Optional[UUID] = Field(
        None,
        description="UUID пользователя",
    )
    event_types: Optional[List[EventType]] = Field(
        None,
        description="Типы событий",
    )
    include_completed: bool = Field(
        True,
        description="Включать завершенные задачи",
    )
    include_overdue: bool = Field(
        True,
        description="Включать просроченные",
    )
    priority_filter: Optional[List[EventPriority]] = Field(
        None,
        description="Фильтр по приоритету",
    )


class CalendarStats(BaseModel):
    """Статистика календаря"""

    period_start: datetime
    period_end: datetime
    total_events: int
    events_by_type: dict[EventType, int] = Field(default_factory=dict)
    events_by_priority: dict[EventPriority, int] = Field(default_factory=dict)
    overdue_count: int = 0
    completed_tasks: int = 0
    upcoming_meetings: int = 0
    busy_days: int = 0  # Дни с событиями


class CalendarUpcoming(BaseModel):
    """Предстоящие события"""

    today: List[CalendarEvent] = Field(default_factory=list)
    tomorrow: List[CalendarEvent] = Field(default_factory=list)
    this_week: List[CalendarEvent] = Field(default_factory=list)
    next_week: List[CalendarEvent] = Field(default_factory=list)
    overdue: List[CalendarEvent] = Field(default_factory=list)
