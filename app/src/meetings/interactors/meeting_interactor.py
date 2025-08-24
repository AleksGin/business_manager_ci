from datetime import (
    datetime,
    timedelta,
)
from typing import (
    List,
    Optional,
)
from uuid import UUID

from src.core.interfaces import (
    DBSession,
    PermissionValidator,
    UUIDGenerator,
)
from src.meetings.interfaces import MeetingRepository
from src.meetings.models import Meeting
from src.meetings.schemas.meeting import MeetingUpdate
from src.teams.interfaces import TeamRepository
from src.users.interfaces import UserRepository
from src.users.models import RoleEnum


class CreateMeetingDTO:
    """DTO для создания встречи"""

    def __init__(
        self,
        title: str,
        description: str,
        date_time: datetime,
        team_uuid: UUID,
        creator_uuid: UUID,
        participants_uuids: Optional[List[UUID]] = None,
    ) -> None:
        self.title = title
        self.description = description
        self.date_time = date_time
        self.team_uuid = team_uuid
        self.creator_uuid = creator_uuid
        self.participants_uuids = participants_uuids or []


class CreateMeetingInteractor:
    """Интерактор для создания встречи"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        team_repo: TeamRepository,
        permission_validator: Optional[PermissionValidator],
        uuid_generator: UUIDGenerator,
        db_session: DBSession,
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._team_repo = team_repo
        self._permission_validator = permission_validator
        self._uuid_generator = uuid_generator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        dto: CreateMeetingDTO,
    ) -> Meeting:
        """Создать новую встречу"""

        try:
            # 1. Найти актора и команду
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            team = await self._team_repo.get_by_uuid(dto.team_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not team:
                raise ValueError("Команда не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_create_meetings(
                    actor, team
                ):
                    raise PermissionError("Нет прав для создания встреч в этой команде")
            else:
                # Временная простая проверка
                is_team_member = actor.team_uuid == team.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager = actor.role == RoleEnum.MANAGER

                if not (is_team_member or is_admin or is_manager):
                    raise PermissionError(
                        "Только участники команды, админы или менеджеры могут создавать встречи"
                    )

            # 3. Бизнес-валидация
            if dto.date_time <= datetime.now():
                raise ValueError("Время встречи должно быть в будущем")

            # Проверить участников
            participants = []
            for participant_uuid in dto.participants_uuids:
                participant = await self._user_repo.get_by_uuid(participant_uuid)
                if not participant:
                    raise ValueError(f"Участник {participant_uuid} не найден")

                # Участники должны быть из той же команды (опционально)
                if participant.team_uuid != team.uuid and actor.role not in [
                    RoleEnum.ADMIN,
                    RoleEnum.MANAGER,
                ]:
                    raise ValueError(
                        f"Участник {participant.email} не состоит в команде"
                    )

                participants.append(participant)

            # 4. Проверить конфликты времени для создателя
            meeting_end_time = dto.date_time + timedelta(hours=1)  # Предполагаем 1 час
            conflicts = await self._meeting_repo.check_time_conflicts(
                user_uuid=actor.uuid,
                start_time=dto.date_time,
                end_time=meeting_end_time,
            )

            if conflicts:
                conflict_meeting = conflicts[0]
                raise ValueError(
                    f"Конфликт времени: у вас уже есть встреча '{conflict_meeting.title}' в {conflict_meeting.date_time}"
                )

            # 5. Создать встречу
            meeting_uuid = self._uuid_generator()

            meeting = Meeting(
                uuid=meeting_uuid,
                title=dto.title,
                description=dto.description,
                date_time=dto.date_time,
                creator_uuid=dto.creator_uuid,
                team_uuid=dto.team_uuid,
            )

            # 6. Сохранить встречу
            created_meeting = await self._meeting_repo.create_meeting(meeting)
            await self._db_session.flush()

            # 7. Добавить участников
            for participant in participants:
                await self._meeting_repo.add_participant(
                    meeting_uuid=created_meeting.uuid,
                    user_uuid=participant.uuid,
                )

            await self._db_session.commit()
            return created_meeting

        except Exception:
            await self._db_session.rollback()
            raise


class GetMeetingInteractor:
    """Интерактор для получения встречи"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def get_by_uuid(
        self,
        actor_uuid: UUID,
        meeting_uuid: UUID,
        with_participants: bool = False,
    ) -> Optional[Meeting]:
        """Получить встречу по UUID"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Получить встречу
        if with_participants:
            meeting = await self._meeting_repo.get_meeting_with_participants(
                meeting_uuid
            )
        else:
            meeting = await self._meeting_repo.get_by_uuid(meeting_uuid)

        if not meeting:
            return None

        # 3. Проверить права доступа
        await self._check_view_permissions(actor, meeting)
        return meeting

    async def _check_view_permissions(self, actor, meeting: Meeting) -> None:
        """Проверить права просмотра встречи"""
        if self._permission_validator:
            # TODO: Добавить метод can_view_meeting в PermissionValidator
            pass
        else:
            # Временная проверка
            is_creator = meeting.creator_uuid == actor.uuid
            is_participant = await self._meeting_repo.is_participant(
                meeting.uuid, actor.uuid
            )
            is_team_member = actor.team_uuid == meeting.team_uuid
            is_admin = actor.role == RoleEnum.ADMIN

            if not (is_creator or is_participant or is_team_member or is_admin):
                raise PermissionError("Нет прав для просмотра встречи")


class UpdateMeetingInteractor:
    """Интерактор для обновления встречи"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        meeting_uuid: UUID,
        update_data: MeetingUpdate,
    ) -> Meeting:
        """Обновить встречу"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            meeting = await self._meeting_repo.get_by_uuid(meeting_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not meeting:
                raise ValueError("Встреча не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_update_meeting(
                    actor, meeting
                ):
                    raise PermissionError("Нет прав для обновления встречи")
            else:
                # Временная простая проверка
                is_creator = meeting.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_creator or is_admin):
                    raise PermissionError(
                        "Только создатель встречи или админ может обновлять встречу"
                    )

            # 3. Валидация изменений
            if update_data.title is not None:
                meeting.title = update_data.title

            if update_data.description is not None:
                meeting.description = update_data.description

            if update_data.date_time is not None:
                # Проверить, что новое время в будущем
                if update_data.date_time <= datetime.now():
                    raise ValueError("Время встречи должно быть в будущем")

                # Проверить конфликты времени для создателя
                meeting_end_time = update_data.date_time + timedelta(hours=1)
                conflicts = await self._meeting_repo.check_time_conflicts(
                    user_uuid=meeting.creator_uuid,
                    start_time=update_data.date_time,
                    end_time=meeting_end_time,
                    exclude_meeting_uuid=meeting.uuid,
                )

                if conflicts:
                    conflict_meeting = conflicts[0]
                    raise ValueError(
                        f"Конфликт времени: уже есть встреча '{conflict_meeting.title}' в {conflict_meeting.date_time}"
                    )

                meeting.date_time = update_data.date_time

            # 4. Сохранить
            updated_meeting = await self._meeting_repo.update_meeting(meeting)
            await self._db_session.commit()
            return updated_meeting

        except Exception:
            await self._db_session.rollback()
            raise


class DeleteMeetingInteractor:
    """Интерактор для удаления встречи"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        meeting_uuid: UUID,
    ) -> bool:
        """Удалить встречу"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            meeting = await self._meeting_repo.get_by_uuid(meeting_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not meeting:
                raise ValueError("Встреча не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_delete_meeting(
                    actor, meeting
                ):
                    raise PermissionError("Нет прав для удаления встречи")
            else:
                # Временная простая проверка
                is_creator = meeting.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_creator or is_admin):
                    raise PermissionError(
                        "Только создатель встречи или админ может удалять встречу"
                    )

            # 3. Удалить встречу (участники удалятся автоматически по CASCADE)
            result = await self._meeting_repo.delete_meeting(meeting_uuid)
            if result:
                await self._db_session.commit()
            return result

        except Exception:
            await self._db_session.rollback()
            raise


class ManageMeetingParticipantsInteractor:
    """Интерактор для управления участниками встречи"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def add_participants(
        self,
        actor_uuid: UUID,
        meeting_uuid: UUID,
        participant_uuids: List[UUID],
    ) -> bool:
        """Добавить участников во встречу"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            meeting = await self._meeting_repo.get_meeting_with_participants(
                meeting_uuid
            )

            if not actor:
                raise ValueError("Пользователь не найден")
            if not meeting:
                raise ValueError("Встреча не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_add_meeting_participant(
                    actor, meeting
                ):
                    raise PermissionError("Нет прав для добавления участников")
            else:
                # Временная простая проверка
                is_creator = meeting.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager_same_team = (
                    actor.role == RoleEnum.MANAGER
                    and actor.team_uuid == meeting.team_uuid
                )

                if not (is_creator or is_admin or is_manager_same_team):
                    raise PermissionError(
                        "Только создатель встречи, админ или менеджер команды может добавлять участников"
                    )

            # 3. Валидация и добавление участников
            added_count = 0
            for participant_uuid in participant_uuids:
                participant = await self._user_repo.get_by_uuid(participant_uuid)
                if not participant:
                    raise ValueError(f"Участник {participant_uuid} не найден")

                # Проверить, что участник активен
                if not participant.is_active:
                    raise ValueError(f"Пользователь {participant.email} неактивен")

                # Добавить участника
                result = await self._meeting_repo.add_participant(
                    meeting_uuid=meeting.uuid,
                    user_uuid=participant.uuid,
                )
                if result:
                    added_count += 1

            await self._db_session.commit()
            return added_count > 0

        except Exception:
            await self._db_session.rollback()
            raise

    async def remove_participants(
        self,
        actor_uuid: UUID,
        meeting_uuid: UUID,
        participant_uuids: List[UUID],
    ) -> bool:
        """Удалить участников из встречи"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            meeting = await self._meeting_repo.get_by_uuid(meeting_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not meeting:
                raise ValueError("Встреча не найдена")

            # 2. Проверить права доступа
            # Участник может удалить только себя
            is_self_removal = (
                len(participant_uuids) == 1 and participant_uuids[0] == actor.uuid
            )

            if not is_self_removal:
                # Проверяем права для удаления других
                is_creator = meeting.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_creator or is_admin):
                    raise PermissionError(
                        "Только создатель встречи или админ может удалять других участников"
                    )

            # 3. Удалить участников
            removed_count = 0
            for participant_uuid in participant_uuids:
                result = await self._meeting_repo.remove_participant(
                    meeting_uuid=meeting.uuid,
                    user_uuid=participant_uuid,
                )
                if result:
                    removed_count += 1

            await self._db_session.commit()
            return removed_count > 0

        except Exception:
            await self._db_session.rollback()
            raise


class QueryMeetingsInteractor:
    """Интерактор для получения списка встреч"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        team_uuid: Optional[UUID] = None,
        creator_uuid: Optional[UUID] = None,
        participant_uuid: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        upcoming_only: bool = False,
        by_date: Optional[datetime] = None,
    ) -> List[Meeting]:
        """Получить список встреч с фильтрацией"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить доступные встречи на основе роли
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только встречи своей команды
            final_team_uuid = actor.team_uuid
            if team_uuid and team_uuid != actor.team_uuid:
                raise PermissionError("Нет прав для просмотра встреч другой команды")
        else:
            # Админы и менеджеры могут указывать команду
            final_team_uuid = team_uuid

        # 3. Получить встречи
        if by_date:
            meetings = await self._meeting_repo.get_meetings_by_date(
                target_date=by_date,
                user_uuid=participant_uuid,
                team_uuid=final_team_uuid,
            )
        elif upcoming_only:
            meetings = await self._meeting_repo.get_upcoming_meetings(
                user_uuid=participant_uuid,
                team_uuid=final_team_uuid,
                limit=limit,
            )
        elif participant_uuid:
            meetings = await self._meeting_repo.get_user_meetings(
                user_uuid=participant_uuid,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset,
            )
        elif final_team_uuid:
            meetings = await self._meeting_repo.get_team_meetings(
                team_uuid=final_team_uuid,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset,
            )
        else:
            meetings = await self._meeting_repo.list_meetings(
                limit=limit,
                offset=offset,
                team_uuid=final_team_uuid,
                creator_uuid=creator_uuid,
                participant_uuid=participant_uuid,
                date_from=date_from,
                date_to=date_to,
            )

        return meetings


class GetMeetingStatsInteractor:
    """Интерактор для получения статистики встреч"""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._meeting_repo = meeting_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
    ) -> dict:
        """Получить статистику встреч"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Проверить права доступа
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только статистику своей команды
            final_team_uuid = actor.team_uuid
            final_user_uuid = user_uuid

            if team_uuid and team_uuid != actor.team_uuid:
                raise PermissionError(
                    "Нет прав для просмотра статистики другой команды"
                )
        else:
            # Админы и менеджеры могут указывать параметры
            final_team_uuid = team_uuid
            final_user_uuid = user_uuid

        # 3. Собрать статистику
        total_meetings_30_days = await self._meeting_repo.count_meetings_by_period(
            user_uuid=final_user_uuid,
            team_uuid=final_team_uuid,
            days=30,
        )

        upcoming_meetings = await self._meeting_repo.get_upcoming_meetings(
            user_uuid=final_user_uuid,
            team_uuid=final_team_uuid,
            limit=100,  # Большой лимит для подсчета
        )

        return {
            "total_meetings_last_30_days": total_meetings_30_days,
            "upcoming_meetings_count": len(upcoming_meetings),
            "user_uuid": str(final_user_uuid) if final_user_uuid else None,
            "team_uuid": str(final_team_uuid) if final_team_uuid else None,
        }
