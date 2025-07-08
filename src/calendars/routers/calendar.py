from calendars.interactors import (
    GetCalendarDayInteractor,
    GetCalendarMonthInteractor,
    GetCalendarStatsInteractor,
    GetCalendarWeekInteractor,
    GetUpcomingEventsInteractor,
)
from calendars.schemas import (
    CalendarDay,
    CalendarFilter,
    CalendarMonth,
    CalendarStats,
    CalendarUpcoming,
    CalendarWeek,
    EventPriority,
    EventType,
)
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from core.dependencies import (
    CurrentUserDep,
    MeetingRepoDep,
    TaskRepoDep,
    UserRepoDep,
)

router = APIRouter()


@router.get(
    "/month/{year}/{month}",
    response_model=CalendarMonth,
    status_code=status.HTTP_200_OK,
)
async def get_calendar_month(
    year: int,
    month: int,
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    team_uuid: Optional[UUID] = Query(
        None,
        description="UUID команды",
    ),
    user_uuid: Optional[UUID] = Query(
        None,
        description="UUID пользователя",
    ),
    event_types: Optional[str] = Query(
        None,
        description="Типы событий через запятую",
    ),
    include_completed: bool = Query(
        True,
        description="Включать завершенные задачи",
    ),
    include_overdue: bool = Query(
        True,
        description="Включать просроченные",
    ),
    priority_filter: Optional[str] = Query(
        None, description="Приоритеты через запятую"
    ),
) -> CalendarMonth:
    """Получить календарь на месяц"""

    # Парсим фильтры
    calendar_filter = None
    if (
        any([team_uuid, user_uuid, event_types, priority_filter])
        or not include_completed
        or not include_overdue
    ):
        parsed_event_types = None
        if event_types:
            try:
                parsed_event_types = [
                    EventType(t.strip()) for t in event_types.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный тип события",
                )

        parsed_priorities = None
        if priority_filter:
            try:
                parsed_priorities = [
                    EventPriority(p.strip()) for p in priority_filter.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный приоритет",
                )

        calendar_filter = CalendarFilter(
            team_uuid=team_uuid,
            user_uuid=user_uuid,
            event_types=parsed_event_types,
            include_completed=include_completed,
            include_overdue=include_overdue,
            priority_filter=parsed_priorities,
        )

    # Создаем интерактор
    interactor = GetCalendarMonthInteractor(
        task_repo=task_repo,
        meeting_repo=meeting_repo,
        user_repo=user_repo,
    )

    try:
        return await interactor(
            actor_uuid=current_user.uuid,
            year=year,
            month=month,
            calendar_filter=calendar_filter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/week",
    response_model=CalendarWeek,
    status_code=status.HTTP_200_OK,
)
async def get_calendar_week(
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    date: datetime = Query(
        ...,
        description="Дата для определения недели",
    ),
    team_uuid: Optional[UUID] = Query(
        None,
        description="UUID команды",
    ),
    user_uuid: Optional[UUID] = Query(
        None,
        description="UUID пользователя",
    ),
    event_types: Optional[str] = Query(
        None,
        description="Типы событий через запятую",
    ),
    include_completed: bool = Query(
        True,
        description="Включать завершенные задачи",
    ),
    include_overdue: bool = Query(
        True,
        description="Включать просроченные",
    ),
    priority_filter: Optional[str] = Query(
        None, description="Приоритеты через запятую"
    ),
) -> CalendarWeek:
    """Получить календарь на неделю"""

    interactor = GetCalendarWeekInteractor(
        task_repo=task_repo,
        meeting_repo=meeting_repo,
        user_repo=user_repo,
    )

    # Парсим фильтры (как в месячном календаре)
    calendar_filter = None
    if (
        any([team_uuid, user_uuid, event_types, priority_filter])
        or not include_completed
        or not include_overdue
    ):
        parsed_event_types = None
        if event_types:
            try:
                parsed_event_types = [
                    EventType(t.strip()) for t in event_types.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный тип события",
                )

        parsed_priorities = None
        if priority_filter:
            try:
                parsed_priorities = [
                    EventPriority(p.strip()) for p in priority_filter.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный приоритет",
                )

        calendar_filter = CalendarFilter(
            team_uuid=team_uuid,
            user_uuid=user_uuid,
            event_types=parsed_event_types,
            include_completed=include_completed,
            include_overdue=include_overdue,
            priority_filter=parsed_priorities,
        )

    try:
        return await interactor(
            actor_uuid=current_user.uuid,
            date=date,
            calendar_filter=calendar_filter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/day",
    response_model=CalendarDay,
    status_code=status.HTTP_200_OK,
)
async def get_calendar_day(
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    date: datetime = Query(..., description="Дата"),
    team_uuid: Optional[UUID] = Query(
        None,
        description="UUID команды",
    ),
    user_uuid: Optional[UUID] = Query(
        None,
        description="UUID пользователя",
    ),
    event_types: Optional[str] = Query(
        None,
        description="Типы событий через запятую",
    ),
    include_completed: bool = Query(
        True,
        description="Включать завершенные задачи",
    ),
    include_overdue: bool = Query(
        True,
        description="Включать просроченные",
    ),
    priority_filter: Optional[str] = Query(
        None, description="Приоритеты через запятую"
    ),
) -> CalendarDay:
    """Получить календарь на день"""

    interactor = GetCalendarDayInteractor(
        task_repo=task_repo,
        meeting_repo=meeting_repo,
        user_repo=user_repo,
    )

    # Парсим фильтры
    calendar_filter = None
    if (
        any([team_uuid, user_uuid, event_types, priority_filter])
        or not include_completed
        or not include_overdue
    ):
        parsed_event_types = None
        if event_types:
            try:
                parsed_event_types = [
                    EventType(t.strip()) for t in event_types.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный тип события",
                )

        parsed_priorities = None
        if priority_filter:
            try:
                parsed_priorities = [
                    EventPriority(p.strip()) for p in priority_filter.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный приоритет",
                )

        calendar_filter = CalendarFilter(
            team_uuid=team_uuid,
            user_uuid=user_uuid,
            event_types=parsed_event_types,
            include_completed=include_completed,
            include_overdue=include_overdue,
            priority_filter=parsed_priorities,
        )

    try:
        return await interactor(
            actor_uuid=current_user.uuid,
            date=date,
            calendar_filter=calendar_filter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/upcoming",
    response_model=CalendarUpcoming,
    status_code=status.HTTP_200_OK,
)
async def get_upcoming_events(
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    team_uuid: Optional[UUID] = Query(
        None,
        description="UUID команды",
    ),
    user_uuid: Optional[UUID] = Query(
        None,
        description="UUID пользователя",
    ),
    event_types: Optional[str] = Query(
        None,
        description="Типы событий через запятую",
    ),
    include_completed: bool = Query(
        True,
        description="Включать завершенные задачи",
    ),
    include_overdue: bool = Query(
        True,
        description="Включать просроченные",
    ),
    priority_filter: Optional[str] = Query(
        None,
        description="Приоритеты через запятую",
    ),
) -> CalendarUpcoming:
    """Получить предстоящие события"""

    interactor = GetUpcomingEventsInteractor(
        task_repo=task_repo,
        meeting_repo=meeting_repo,
        user_repo=user_repo,
    )

    # Парсим фильтры
    calendar_filter = None
    if (
        any([team_uuid, user_uuid, event_types, priority_filter])
        or not include_completed
        or not include_overdue
    ):
        parsed_event_types = None
        if event_types:
            try:
                parsed_event_types = [
                    EventType(t.strip()) for t in event_types.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный тип события",
                )

        parsed_priorities = None
        if priority_filter:
            try:
                parsed_priorities = [
                    EventPriority(p.strip()) for p in priority_filter.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный приоритет",
                )

        calendar_filter = CalendarFilter(
            team_uuid=team_uuid,
            user_uuid=user_uuid,
            event_types=parsed_event_types,
            include_completed=include_completed,
            include_overdue=include_overdue,
            priority_filter=parsed_priorities,
        )

    try:
        return await interactor(
            actor_uuid=current_user.uuid,
            calendar_filter=calendar_filter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/stats",
    response_model=CalendarStats,
    status_code=status.HTTP_200_OK,
)
async def get_calendar_stats(
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    meeting_repo: MeetingRepoDep,
    user_repo: UserRepoDep,
    start_date: datetime = Query(
        ...,
        description="Начальная дата",
    ),
    end_date: datetime = Query(
        ...,
        description="Конечная дата",
    ),
    team_uuid: Optional[UUID] = Query(
        None,
        description="UUID команды",
    ),
    user_uuid: Optional[UUID] = Query(
        None,
        description="UUID пользователя",
    ),
    event_types: Optional[str] = Query(
        None,
        description="Типы событий через запятую",
    ),
    include_completed: bool = Query(
        True,
        description="Включать завершенные задачи",
    ),
    include_overdue: bool = Query(
        True,
        description="Включать просроченные",
    ),
    priority_filter: Optional[str] = Query(
        None,
        description="Приоритеты через запятую",
    ),
) -> CalendarStats:
    """Получить статистику календаря за период"""

    interactor = GetCalendarStatsInteractor(
        task_repo=task_repo,
        meeting_repo=meeting_repo,
        user_repo=user_repo,
    )

    # Парсим фильтры
    calendar_filter = None
    if (
        any([team_uuid, user_uuid, event_types, priority_filter])
        or not include_completed
        or not include_overdue
    ):
        parsed_event_types = None
        if event_types:
            try:
                parsed_event_types = [
                    EventType(t.strip()) for t in event_types.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный тип события",
                )

        parsed_priorities = None
        if priority_filter:
            try:
                parsed_priorities = [
                    EventPriority(p.strip()) for p in priority_filter.split(",")
                ]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный приоритет",
                )

        calendar_filter = CalendarFilter(
            team_uuid=team_uuid,
            user_uuid=user_uuid,
            event_types=parsed_event_types,
            include_completed=include_completed,
            include_overdue=include_overdue,
            priority_filter=parsed_priorities,
        )

    try:
        return await interactor(
            actor_uuid=current_user.uuid,
            start_date=start_date,
            end_date=end_date,
            calendar_filter=calendar_filter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
