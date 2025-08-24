from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from src.core.dependencies import (
    CurrentUserDep,
    SessionDep,
    TaskRepoDep,
    TeamRepoDep,
    UUIDGeneratorDep,
    UserRepoDep,
)
from src.tasks.interactors import (
    AssignTaskInteractor,
    ChangeTaskStatusInteractor,
    CreateTaskDTO,
    CreateTaskInteractor,
    DeleteTaskInteractor,
    GetTaskInteractor,
    GetTaskStatsInteractor,
    QueryTasksInteractor,
    UpdateTaskInteractor,
)
from src.tasks.models import StatusEnum
from src.tasks.schemas.task import (
    TaskAssign,
    TaskCreate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
    TaskWithDetails,
)

router = APIRouter()


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    task_data: TaskCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
    team_repo: TeamRepoDep,
    uuid_generator: UUIDGeneratorDep,
) -> TaskResponse:
    """Создать новую задачу"""

    dto = CreateTaskDTO(
        title=task_data.title,
        description=task_data.description,
        deadline=task_data.deadline,
        team_uuid=task_data.team_uuid,
        assignee_uuid=task_data.assignee_uuid,
        creator_uuid=current_user.uuid,
    )

    interactor = CreateTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        team_repo=team_repo,
        permission_validator=None,
        uuid_generator=uuid_generator,
        db_session=session,
    )

    try:
        task = await interactor(
            actor_uuid=current_user.uuid,
            dto=dto,
        )
        return TaskResponse.model_validate(task)

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
    "/",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
)
async def list_tasks(
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    team_uuid: Optional[UUID] = Query(default=None),
    assignee_uuid: Optional[UUID] = Query(default=None),
    creator_uuid: Optional[UUID] = Query(default=None),
    task_status: Optional[StatusEnum] = Query(default=None),
    search: Optional[str] = Query(default=None),
    show_overdue: bool = Query(default=False),
) -> List[TaskResponse]:
    """Получить список задач"""

    interactor = QueryTasksInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        tasks = await interactor(
            actor_uuid=current_user.uuid,
            limit=limit,
            offset=offset,
            team_uuid=team_uuid,
            assignee_uuid=assignee_uuid,
            creator_uuid=creator_uuid,
            status=task_status,
            search_query=search,
            show_overdue=show_overdue,
        )
        return [TaskResponse.model_validate(task) for task in tasks]

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
    "/{task_uuid}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def get_task(
    task_uuid: UUID,
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> TaskResponse:
    """Получить задачу по UUID"""

    interactor = GetTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        task = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
            with_relations=False,
        )

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена",
            )

        return TaskResponse.model_validate(task)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{task_uuid}/details",
    response_model=TaskWithDetails,
    status_code=status.HTTP_200_OK,
)
async def get_task_with_details(
    task_uuid: UUID,
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> TaskWithDetails:
    """Получить задачу с деталями (исполнитель, создатель)"""

    interactor = GetTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        task = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
            with_relations=True,
        )

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена",
            )

        return TaskWithDetails.model_validate(task)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{task_uuid}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def update_task(
    task_uuid: UUID,
    update_data: TaskUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> TaskResponse:
    """Обновить задачу"""

    interactor = UpdateTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        task = await interactor(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
            update_data=update_data,
        )

        return TaskResponse.model_validate(task)

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


@router.delete(
    "/{task_uuid}",
    status_code=status.HTTP_200_OK,
)
async def delete_task(
    task_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Удалить задачу"""

    interactor = DeleteTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена",
            )

        return {"message": "Задача успешно удалена"}

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{task_uuid}/assign",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_task(
    task_uuid: UUID,
    assign_data: TaskAssign,
    current_user: CurrentUserDep,
    session: SessionDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> TaskResponse:
    """Назначить исполнителя задачи"""

    interactor = AssignTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        task = await interactor(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
            assignee_uuid=assign_data.assignee_uuid,
        )

        return TaskResponse.model_validate(task)

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


@router.post(
    "/{task_uuid}/unassign",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def unassign_task(
    task_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> TaskResponse:
    """Снять исполнителя с задачи"""

    interactor = AssignTaskInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        task = await interactor(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
            assignee_uuid=None,  # Снимаем исполнителя
        )

        return TaskResponse.model_validate(task)

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


@router.patch(
    "/{task_uuid}/status",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def change_task_status(
    task_uuid: UUID,
    status_data: TaskStatusUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
) -> TaskResponse:
    """Изменить статус задачи"""

    interactor = ChangeTaskStatusInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        task = await interactor(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
            new_status=status_data.status,
        )

        return TaskResponse.model_validate(task)

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
    "/stats/overview",
    status_code=status.HTTP_200_OK,
)
async def get_task_stats(
    current_user: CurrentUserDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
    team_uuid: Optional[UUID] = Query(default=None),
    assignee_uuid: Optional[UUID] = Query(default=None),
) -> Dict[str, Any]:
    """Получить статистику задач"""

    interactor = GetTaskStatsInteractor(
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        stats = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
            assignee_uuid=assignee_uuid,
        )

        return stats

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
