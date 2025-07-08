from typing import (
    Any,
    Dict,
)

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)

from core.dependencies import (
    CurrentUserDep,
    PasswordHasherDep,
    SessionDep,
    TokenRepoDep,
    UserActivationDep,
    UserRepoDep,
    UserValidatorDep,
    UUIDGeneratorDep,
    PermissionValidatorDep,
)
from core.models import TokenType
from core.providers import (
    jwt_provider,
)
from users.interactors.auth_interactors import (
    AuthenticateUserInteractor,
    ChangePasswordInteractor,
    ConfirmPasswordResetInteractor,
    RequestPasswordResetInteractor,
    VerifyEmailInteractor,
)
from users.interactors.user_interactos import (
    CreateUserDTO,
    CreateUserInteractor,
)
from users.schemas.user import (
    UserChangePassword,
    UserCreate,
    UserLogin,
    UserResponse,
    UserTokenResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    session: SessionDep,
    user_repo: UserRepoDep,
    password_hasher: PasswordHasherDep,
    user_validator: UserValidatorDep,
    uuid_generator: UUIDGeneratorDep,
    token_repo: TokenRepoDep,
    activation_manager: UserActivationDep,
    permission_validator: PermissionValidatorDep,
) -> UserTokenResponse:
    """Регистрация нового пользователя"""

    # Создаем DTO для интерактора
    dto = CreateUserDTO(
        email=user_data.email,
        name=user_data.name,
        surname=user_data.surname,
        gender=user_data.gender,
        birth_date=user_data.birth_date,
        password=user_data.password,
    )

    # Создаем интерактор

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
        # Создание пользователя (actor_uuid=None для самостоятельной регистрации)
        user = await create_user_interactor(
            actor_uuid=None,
            dto=dto,
        )

        # Генерируем токены
        tokens = jwt_provider.create_token_pair(
            user_uuid=user.uuid,
            user_role=user.role.value if user.role else "EMPLOYEE",
        )

        # Сохраняем refresh токен в БД
        refresh_token_hash = jwt_provider.hash_refresh_token(tokens["refresh_token"])
        expires_at = jwt_provider.get_refresh_token_expires_at()

        await token_repo.create_token(
            user_uuid=user.uuid,
            token_hash=refresh_token_hash,
            token_type=TokenType.REFRESH,
            expires_at=expires_at,
        )

        await session.commit()

        return UserTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            user=UserResponse.model_validate(user),
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
    "/login",
    response_model=UserTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    credentials: UserLogin,
    request: Request,
    session: SessionDep,
    user_repo: UserRepoDep,
    password_hasher: PasswordHasherDep,
    token_repo: TokenRepoDep,
) -> UserTokenResponse:
    """Вход в систему"""

    # Создаем интерактор аутентификации
    auth_interactor = AuthenticateUserInteractor(
        user_repo=user_repo,
        password_hasher=password_hasher,
    )

    try:
        user = await auth_interactor(
            credentials.email,
            credentials.password,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
            )

        # Генерируем токены
        tokens = jwt_provider.create_token_pair(
            user_uuid=user.uuid,
            user_role=user.role.value if user.role else "EMPLOYEE",
        )

        # Сохраняем refresh токен
        refresh_token_hash = jwt_provider.hash_refresh_token(tokens["refresh_token"])
        expires_at = jwt_provider.get_refresh_token_expires_at()

        # Получаем IP и User-Agent из запроса
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        await token_repo.create_token(
            user_uuid=user.uuid,
            token_hash=refresh_token_hash,
            token_type=TokenType.REFRESH,
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        await session.commit()

        return UserTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            user=UserResponse.model_validate(user),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: CurrentUserDep,
    session: SessionDep,
    token_repo: TokenRepoDep,
) -> Dict[str, str]:
    """Выход из системы (деактивация всех refresh токенов)"""

    count = await token_repo.revoke_all_user_sessions(current_user.uuid)
    await session.commit()

    return {"message": f"Выход выполнен. Деактивировано сессий: {count}"}


@router.post(
    "/refresh",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
)
async def refresh_token(
    refresh_token: str,
    session: SessionDep,
    user_repo: UserRepoDep,
    token_repo: TokenRepoDep,
) -> Dict[str, Any]:
    """Обновление access токена с помощью refresh токена"""

    # Хешируем переданный токен
    token_hash = jwt_provider.hash_refresh_token(refresh_token)

    # Ищем токен в БД
    token_record = await token_repo.get_token_by_hash(
        token_hash,
        TokenType.REFRESH,
    )

    if not token_record or not token_record.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh токен",
        )

    # Получаем пользователя
    user = await user_repo.get_by_uuid(token_record.user_uuid)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или не активен",
        )

    # Генерируем новые токены
    new_tokens = jwt_provider.create_token_pair(
        user_uuid=user.uuid,
        user_role=user.role.value if user.role else "EMPLOYEE",
    )

    # Обновляем refresh токен в БД
    new_refresh_hash = jwt_provider.hash_refresh_token(new_tokens["refresh_token"])
    new_expires_at = jwt_provider.get_refresh_token_expires_at()

    await token_repo.rotate_refresh_token(
        old_token_hash=token_hash,
        new_token_hash=new_refresh_hash,
        new_expires_at=new_expires_at,
        user_uuid=user.uuid,
    )

    await session.commit()

    return {
        "access_token": new_tokens["access_token"],
        "refresh_token": new_tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
)
async def change_password(
    passwords: UserChangePassword,
    current_user: CurrentUserDep,
    session: SessionDep,
    user_repo: UserRepoDep,
    password_hasher: PasswordHasherDep,
    user_validator: UserValidatorDep,
    permission_validator: PermissionValidatorDep,
) -> Dict[str, str]:
    """Смена пароля"""

    change_password_interactor = ChangePasswordInteractor(
        user_repo=user_repo,
        password_hasher=password_hasher,
        user_validator=user_validator,
        permission_validator=permission_validator,
        db_session=session,
    )

    try:
        result = await change_password_interactor(
            actor_uuid=current_user.uuid,
            target_uuid=current_user.uuid,
            current_password=passwords.current_password,
            new_password=passwords.new_password,
        )

        if result:
            return {"message": "Пароль успешно изменен"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось изменить",
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUserDep) -> UserResponse:
    """Получить информацию о текущем пользователе"""
    return UserResponse.model_validate(current_user)


@router.post(
    "/request-password-reset",
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    email: str,
    session: SessionDep,
    activation_manager: UserActivationDep,
) -> Dict[str, str]:
    """Запрос на сброс пароля"""

    reset_interactor = RequestPasswordResetInteractor(
        activation_manager=activation_manager,
        db_session=session,
    )

    try:
        token = await reset_interactor(email)

        # В реальном приложении здесь была бы отправка email
        return {
            "messsage": "Инструкция по сбросу пароля отправлены на email",
            "token": token,
        }

    except Exception as e:
        # Возвращаем общий ответ
        return {"message": "Если email существует, инструкции будут отправлены"}


@router.post(
    "/confirm-password-reset",
    status_code=status.HTTP_200_OK,
)
async def confirm_password_reset(
    token: str,
    new_password: str,
    session: SessionDep,
    activation_manager: UserActivationDep,
) -> Dict[str, str]:
    """Подтверждение сброс пароля"""

    confirm_interactor = ConfirmPasswordResetInteractor(
        activation_manager=activation_manager,
        db_session=session,
    )

    try:
        result = await confirm_interactor(
            token,
            new_password,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недействительный или истекший токен",
            )

        return {"message": "Пароль успешно изменен"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/request-email-verification",
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_email_verification(
    current_user: CurrentUserDep,
    session: SessionDep,
    activation_manager: UserActivationDep,
):
    """
    Запросить повторную отправку токена для верификации
    *Сделано для теста API, на самом деле запрос на подтверждение email отправляется при регистрации*
    """

    if current_user.is_verified:
        return {"message": "Email уже подтвержден"}

    try:
        verification_token = await activation_manager.generate_verification_token(
            current_user.uuid
        )
        await session.commit()

        return {
            "message": "Токен верификации отправлен на email",
            "verification_token": verification_token,
        }

    except Exception as e:
        return {"message:Не удалось отправить токен верификации"}


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
)
async def verify_email(
    token: str,
    current_user: CurrentUserDep,
    session: SessionDep,
    activation_manager: UserActivationDep,
) -> Dict[str, str]:
    """Подтверждение email"""

    verify_interactor = VerifyEmailInteractor(
        activation_manager=activation_manager,
        db_session=session,
    )

    try:
        result = await verify_interactor(
            current_user.uuid,
            token,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недействительный или истекший токен",
            )

        return {"messsage": "Email успешно подтвержден"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
