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

from core.dependencies import (
    CurrentUserDep,
    EvaluationRepoDep,
    SessionDep,
    TaskRepoDep,
    UUIDGeneratorDep,
    UserRepoDep,
)
from evaluations.interactors import (
    CreateEvaluationDTO,
    CreateEvaluationInteractor,
    DeleteEvaluationInteractor,
    GetEvaluationInteractor,
    GetTeamEvaluationStatsInteractor,
    GetUserEvaluationStatsInteractor,
    QueryEvaluationsInteractor,
    UpdateEvaluationInteractor,
)
from evaluations.models import ScoresEnum
from evaluations.schemas.evaluation import (
    EvaluationCreate,
    EvaluationResponse,
    EvaluationUpdate,
    EvaluationWithDetails,
)

router = APIRouter()


@router.post(
    "/",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation(
    evaluation_data: EvaluationCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
    evaluation_repo: EvaluationRepoDep,
    task_repo: TaskRepoDep,
    user_repo: UserRepoDep,
    uuid_generator: UUIDGeneratorDep,
) -> EvaluationResponse:
    """Создать новую оценку"""

    dto = CreateEvaluationDTO(
        task_uuid=evaluation_data.task_uuid,
        evaluated_user_uuid=evaluation_data.evaluated_user_uuid,
        score=evaluation_data.score,
        comment=evaluation_data.comment,
        evaluator_uuid=current_user.uuid,
    )

    interactor = CreateEvaluationInteractor(
        evaluation_repo=evaluation_repo,
        task_repo=task_repo,
        user_repo=user_repo,
        permission_validator=None,
        uuid_generator=uuid_generator,
        db_session=session,
    )

    try:
        evaluation = await interactor(
            actor_uuid=current_user.uuid,
            dto=dto,
        )
        return EvaluationResponse.model_validate(evaluation)

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
    response_model=List[EvaluationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_evaluations(
    current_user: CurrentUserDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user_uuid: Optional[UUID] = Query(
        default=None, description="UUID пользователя (получившего оценки)"
    ),
    evaluator_uuid: Optional[UUID] = Query(
        default=None, description="UUID оценивающего"
    ),
    team_uuid: Optional[UUID] = Query(default=None, description="UUID команды"),
    score: Optional[ScoresEnum] = Query(default=None, description="Фильтр по оценке"),
) -> List[EvaluationResponse]:
    """Получить список оценок"""

    interactor = QueryEvaluationsInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        evaluations = await interactor(
            actor_uuid=current_user.uuid,
            limit=limit,
            offset=offset,
            user_uuid=user_uuid,
            evaluator_uuid=evaluator_uuid,
            team_uuid=team_uuid,
            score=score,
        )
        return [
            EvaluationResponse.model_validate(evaluation) for evaluation in evaluations
        ]

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
    "/{evaluation_uuid}",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_evaluation(
    evaluation_uuid: UUID,
    current_user: CurrentUserDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> EvaluationResponse:
    """Получить оценку по UUID"""

    interactor = GetEvaluationInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        evaluation = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            evaluation_uuid=evaluation_uuid,
            with_relations=False,
        )

        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оценка не найдена",
            )

        return EvaluationResponse.model_validate(evaluation)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{evaluation_uuid}/details",
    response_model=EvaluationWithDetails,
    status_code=status.HTTP_200_OK,
)
async def get_evaluation_with_details(
    evaluation_uuid: UUID,
    current_user: CurrentUserDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> EvaluationWithDetails:
    """Получить оценку с деталями (оценивающий, оцениваемый)"""

    interactor = GetEvaluationInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        evaluation = await interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            evaluation_uuid=evaluation_uuid,
            with_relations=True,
        )

        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оценка не найдена",
            )

        return EvaluationWithDetails.model_validate(evaluation)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/by-task/{task_uuid}",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_evaluation_by_task(
    task_uuid: UUID,
    current_user: CurrentUserDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> EvaluationResponse:
    """Получить оценку по UUID задачи"""

    interactor = GetEvaluationInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        evaluation = await interactor.get_by_task_uuid(
            actor_uuid=current_user.uuid,
            task_uuid=task_uuid,
        )

        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оценка для этой задачи не найдена",
            )

        return EvaluationResponse.model_validate(evaluation)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{evaluation_uuid}",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_evaluation(
    evaluation_uuid: UUID,
    update_data: EvaluationUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> EvaluationResponse:
    """Обновить оценку"""

    interactor = UpdateEvaluationInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        evaluation = await interactor(
            actor_uuid=current_user.uuid,
            evaluation_uuid=evaluation_uuid,
            update_data=update_data,
        )

        return EvaluationResponse.model_validate(evaluation)

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
    "/{evaluation_uuid}",
    status_code=status.HTTP_200_OK,
)
async def delete_evaluation(
    evaluation_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, str]:
    """Удалить оценку"""

    interactor = DeleteEvaluationInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            evaluation_uuid=evaluation_uuid,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оценка не найдена",
            )

        return {"message": "Оценка успешно удалена"}

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/stats/user/{user_uuid}",
    status_code=status.HTTP_200_OK,
)
async def get_user_evaluation_stats(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, Any]:
    """Получить статистику оценок пользователя"""

    interactor = GetUserEvaluationStatsInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        stats = await interactor(
            actor_uuid=current_user.uuid,
            target_user_uuid=user_uuid,
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


@router.get(
    "/stats/team/{team_uuid}",
    status_code=status.HTTP_200_OK,
)
async def get_team_evaluation_stats(
    team_uuid: UUID,
    current_user: CurrentUserDep,
    evaluation_repo: EvaluationRepoDep,
    user_repo: UserRepoDep,
) -> Dict[str, Any]:
    """Получить статистику оценок команды"""

    interactor = GetTeamEvaluationStatsInteractor(
        evaluation_repo=evaluation_repo,
        user_repo=user_repo,
        permission_validator=None,
    )

    try:
        stats = await interactor(
            actor_uuid=current_user.uuid,
            team_uuid=team_uuid,
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
