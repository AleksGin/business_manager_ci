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

from core.dependencies.depends import (
    CurrentUserDep,
    PasswordHasherDep,
    SessionDep,
    UserActivationDep,
    UserRepoDep,
    UserValidatorDep,
    UUIDGeneratorDep,
    TeamMembershipDep,
    PermissionValidatorDep,
    TeamRepoDep,
)
from users.models import RoleEnum
from users.interactors.user_interactos import (
    CreateUserDTO,
    CreateUserInteractor,
    DeleteUserInteractor,
    GetUserInteractor,
    GetUsersWithoutTeamInteractor,
    QueryUserInteractor,
    UpdateUserInteractor,
    AssignRoleInteractor,
    RemoveRoleInteractor,
    LeaveTeamInteractor,
    GetUserStatsInteractor,
    JoinTeamByCodeInteractor,
)
from users.interactors.auth_interactors import AdminActivateUserInteractor
from users.schemas.user import (
    UserCreate,
    UserInTeam,
    UserResponse,
    UserUpdate,
    UserAssignRole,
    UserJoinTeam,
)

router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_data: UserCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    password_hasher: PasswordHasherDep,
    user_validator: UserValidatorDep,
    uuid_generator: UUIDGeneratorDep,
    activation_manager: UserActivationDep,
    permission_validator: PermissionValidatorDep,
) -> UserResponse:
    """Создание нового пользователя"""

    dto = CreateUserDTO(
        email=user_data.email,
        name=user_data.name,
        surname=user_data.surname,
        gender=user_data.gender,
        birth_date=user_data.birth_date,
        password=user_data.password,
    )

    create_user_interactor = CreateUserInteractor(
        user_repo=user_repo,
        password_hasher=password_hasher,
        user_validator=user_validator,
        permission_validator=permission_validator,
        uuid_generator=uuid_generator,
        db_session=session,
        activate_manager=activation_manager,
    )

    try:
        user = await create_user_interactor(
            actor_uuid=current_user.uuid,
            dto=dto,
        )
        return UserResponse.model_validate(user)

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
    response_model=List[UserInTeam],
    status_code=status.HTTP_200_OK,
)
async def list_users(
    current_user: CurrentUserDep,
    user_repo: UserRepoDep,
    team_repo: TeamRepoDep,
    permission_validator: PermissionValidatorDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    team_uuid: Optional[UUID] = Query(default=None),
) -> List[UserInTeam]:
    """Получить список пользователей"""

    get_list_users_interactor = QueryUserInteractor(
        user_repo=user_repo,
        team_repo=team_repo,
        permission_validator=permission_validator,
    )

    try:
        users = await get_list_users_interactor(
            actor_uuid=current_user.uuid,
            limit=limit,
            offset=offset,
            team_uuid=team_uuid,
        )
        return [UserInTeam.model_validate(user) for user in users]

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
    "/{user_uuid}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
) -> UserResponse:
    """Получить пользователя по UUID"""

    get_user_interactor = GetUserInteractor(
        user_repo=user_repo,
        permission_validator=permission_validator,
    )

    try:
        user = await get_user_interactor.get_by_uuid(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        return UserResponse.model_validate(user)

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{user_uuid}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user(
    user_uuid: UUID,
    update_data: UserUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    user_validator: UserValidatorDep,
    permission_validator: PermissionValidatorDep,
) -> UserResponse:
    """Обновить пользователя"""

    update_user_interactor = UpdateUserInteractor(
        user_repo=user_repo,
        user_validator=user_validator,
        permission_validator=permission_validator,
        db_session=session,
    )

    try:
        user = await update_user_interactor(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
            update_data=update_data,
        )

        return UserResponse.model_validate(user)

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
    "/{user_uuid}",
    status_code=status.HTTP_200_OK,
)
async def delete_user(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Удалить пользователя"""

    delete_user_interactor = DeleteUserInteractor(
        user_repo=user_repo,
        permission_validator=permission_validator,
        db_session=session,
    )

    try:
        result = await delete_user_interactor(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        return {"message": "Пользователь успешно удален"}

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/search/",
    response_model=List[UserInTeam],
    status_code=status.HTTP_200_OK,
)
async def search_users(
    current_user: CurrentUserDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
    team_repo: TeamRepoDep,
    limit: int = Query(default=20, le=50),
    team_uuid: Optional[UUID] = Query(default=None),
    exclude_team: bool = Query(default=False),
    q: str = Query(min_length=2, description="Поисковый запрос"),
) -> List[UserInTeam]:
    """Поиск пользователей"""

    search_user_interactor = QueryUserInteractor(
        user_repo=user_repo,
        team_repo=team_repo,
        permission_validator=permission_validator,
    )

    users = await search_user_interactor(
        actor_uuid=current_user.uuid,
        limit=limit,
        team_uuid=team_uuid,
        search_query=q,
        exclude_team=exclude_team,
    )

    return [UserInTeam.model_validate(user) for user in users]


@router.get(
    "/without-team/",
    response_model=List[UserInTeam],
    status_code=status.HTTP_200_OK,
)
async def get_users_without_team(
    current_user: CurrentUserDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> List[UserInTeam]:
    """Получить пользователей без команды (только для админов/менеджеров)"""

    # Создаем интерактора
    interactor = GetUsersWithoutTeamInteractor(
        user_repo=user_repo,
        permission_validator=permission_validator,
    )
    try:
        users = await interactor(
            actor_uuid=current_user.uuid,
            limit=limit,
            offset=offset,
        )

        return [UserInTeam.model_validate(user) for user in users]

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{user_uuid}/assign-role",
    status_code=status.HTTP_200_OK,
)
async def assign_role(
    user_uuid: UUID,
    role_data: UserAssignRole,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Назначить роль пользователю (только для админов)"""

    interactor = AssignRoleInteractor(
        user_repo=user_repo,
        permission_validator=permission_validator,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
            new_role=role_data.role,
        )

        if result:
            return {"message": f"Роль {role_data.role.value} успешно назначена"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось назначить роль",
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


@router.delete(
    "/{user_uuid}/role",
    status_code=status.HTTP_200_OK,
)
async def remove_role(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Убрать роль пользователя (сделать EMPLOYEE)"""

    interactor = RemoveRoleInteractor(
        user_repo=user_repo,
        permission_validator=permission_validator,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
        )

        if result:
            return {"message": "Роль убрана, пользователь теперь EMPLOYEE"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось убрать роль",
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


@router.post(
    "/{user_uuid}/activate",
    status_code=status.HTTP_200_OK,
)
async def activate_user(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    activation_manager: UserActivationDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Активировать пользователя (только для админов)"""

    activate_interactor = AdminActivateUserInteractor(
        activation_manager=activation_manager,
        permission_validator=permission_validator,
        user_repo=user_repo,
        db_session=session,
    )

    try:
        result = await activate_interactor.activate(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
        )

        if result:
            return {"message": "Пользователь успешно активирован"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось активировать пользователя",
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


@router.post(
    "/{user_uuid}/deactivate",
    status_code=status.HTTP_200_OK,
)
async def deactivate_user(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    activation_manager: UserActivationDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Деактивировать пользователя (только для админов)"""

    activate_interactor = AdminActivateUserInteractor(
        activation_manager=activation_manager,
        permission_validator=permission_validator,
        user_repo=user_repo,
        db_session=session,
    )

    try:
        result = await activate_interactor.deactivate(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
        )

        if result:
            return {"message": "Пользователь успешно деактивирован"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось деактивировать пользователя",
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


@router.post(
    "/{user_uuid}/join-team-by-code",
    status_code=status.HTTP_200_OK,
)
async def join_team_by_code(
    user_uuid: UUID,
    team_data: UserJoinTeam,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    membership_manager: TeamMembershipDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Присоединиться к команде по коду приглашения"""

    interactor = JoinTeamByCodeInteractor(
        user_repo=user_repo,
        team_membership_manager=membership_manager,
        permission_validator=permission_validator,
        db_session=session,
    )

    try:
        result = await interactor(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
            invite_code=team_data.invite_code,
        )

        if result:
            return {"message": "Успешно присоединился к команде"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось присоединиться к команде",
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
    "/{user_uuid}/stats",
    status_code=status.HTTP_200_OK,
)
async def get_user_stats(
    user_uuid: UUID,
    current_user: CurrentUserDep,
    user_repo: UserRepoDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, Any]:
    """Получить статистику пользователя"""

    interactor = GetUserStatsInteractor(
        user_repo=user_repo,
        permission_validator=permission_validator,
    )

    try:
        stats = await interactor(
            actor_uuid=current_user.uuid,
            target_uuid=user_uuid,
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


# TODO УДАЛИТЬ ЭТОТ ЭНДПОИНТ
@router.post("/make-first-admin")
async def make_admin(
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
):
    """Сделать первого админа"""

    current_user.role = RoleEnum.ADMIN
    await user_repo.update_user(current_user)
    await session.commit()

    return {"message": f"Вы теперь администратор {current_user.email}"}
