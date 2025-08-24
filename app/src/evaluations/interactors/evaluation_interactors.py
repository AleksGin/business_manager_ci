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
from src.evaluations.interfaces import EvaluationRepository
from src.evaluations.models import (
    Evaluation,
    ScoresEnum,
)
from src.evaluations.schemas.evaluation import EvaluationUpdate
from src.users.models import User
from src.tasks.interfaces import TaskRepository
from src.tasks.models import StatusEnum
from src.users.interfaces import UserRepository
from src.users.models import RoleEnum


class CreateEvaluationDTO:
    """DTO для создания оценки"""

    def __init__(
        self,
        task_uuid: UUID,
        evaluated_user_uuid: UUID,
        score: ScoresEnum,
        evaluator_uuid: UUID,
        comment: Optional[str] = None,
    ) -> None:
        self.task_uuid = task_uuid
        self.evaluated_user_uuid = evaluated_user_uuid
        self.score = score
        self.evaluator_uuid = evaluator_uuid
        self.comment = comment


class CreateEvaluationInteractor:
    """Интерактор для создания оценки"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        uuid_generator: UUIDGenerator,
        db_session: DBSession,
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._uuid_generator = uuid_generator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        dto: CreateEvaluationDTO,
    ) -> Evaluation:
        """Создать новую оценку"""

        try:
            # 1. Найти всех участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            task = await self._task_repo.get_by_uuid(dto.task_uuid)
            evaluated_user = await self._user_repo.get_by_uuid(dto.evaluated_user_uuid)

            if not actor:
                raise ValueError("Пользователь не найден")
            if not task:
                raise ValueError("Задача не найдена")
            if not evaluated_user:
                raise ValueError("Оцениваемый пользователь не найден")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_create_evaluation(
                    actor, task
                ):
                    raise PermissionError("Нет прав для создания оценки")
            else:
                # Временная простая проверка
                is_task_creator = task.creator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN
                is_manager_same_team = (
                    actor.role == RoleEnum.MANAGER and actor.team_uuid == task.team_uuid
                )

                if not (is_task_creator or is_admin or is_manager_same_team):
                    raise PermissionError(
                        "Только создатель задачи, админ или менеджер команды может создавать оценки"
                    )

            # 3. Бизнес-валидация
            if task.status != StatusEnum.DONE:
                raise ValueError("Можно оценивать только выполненные задачи")

            # Проверить, что оцениваемый пользователь связан с задачей
            if dto.evaluated_user_uuid != task.assignee_uuid:
                raise ValueError("Можно оценивать только исполнителя задачи")

            # Проверить, что оценка еще не существует
            existing_evaluation = await self._evaluation_repo.get_by_task_uuid(
                dto.task_uuid
            )
            if existing_evaluation:
                raise ValueError("Оценка для этой задачи уже существует")

            # 4. Создать оценку
            evaluation_uuid = self._uuid_generator()

            evaluation = Evaluation(
                uuid=evaluation_uuid,
                task_uuid=dto.task_uuid,
                evaluator_uuid=dto.evaluator_uuid,
                evaluated_user_uuid=dto.evaluated_user_uuid,
                score=dto.score,
                comment=dto.comment,
            )

            # 5. Сохранить
            created_evaluation = await self._evaluation_repo.create_evaluation(
                evaluation
            )
            await self._db_session.commit()
            return created_evaluation

        except Exception:
            await self._db_session.rollback()
            raise


class GetEvaluationInteractor:
    """Интерактор для получения оценки"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def get_by_uuid(
        self,
        actor_uuid: UUID,
        evaluation_uuid: UUID,
        with_relations: bool = False,
    ) -> Optional[Evaluation]:
        """Получить оценку по UUID"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. ВСЕГДА загружаем с relations для проверки прав
        evaluation = await self._evaluation_repo.get_evaluation_with_relations(
            evaluation_uuid
        )
        if not evaluation:
            return None

        # 3. Проверить права доступа с полной информацией
        await self._check_view_permissions(actor, evaluation)

        # 4. Вернуть в нужном формате
        if with_relations:
            return evaluation
        else:
            # Возвращаем "облегченную" версию
            return await self._evaluation_repo.get_by_uuid(evaluation_uuid)

    async def get_by_task_uuid(
        self,
        actor_uuid: UUID,
        task_uuid: UUID,
    ) -> Optional[Evaluation]:
        """Получить оценку по UUID задачи"""

        evaluation = await self._evaluation_repo.get_by_task_uuid(task_uuid)
        if not evaluation:
            return None

        # Используем существующий метод для проверки прав
        return await self.get_by_uuid(actor_uuid, evaluation.uuid, with_relations=False)

    async def _check_view_permissions(
        self,
        actor: "User",
        evaluation: Evaluation,
    ) -> None:
        """Проверить права просмотра оценки"""
        if self._permission_validator and evaluation.task:
            if not await self._permission_validator.can_view_evaluation(
                actor,
                evaluation.task,
            ):
                raise PermissionError("Нет прав для просмотра оценки")
        else:
            # Временная проверка с полной информацией
            is_evaluator = evaluation.evaluator_uuid == actor.uuid
            is_evaluated = evaluation.evaluated_user_uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN
            is_team_member = (
                evaluation.task and actor.team_uuid == evaluation.task.team_uuid
            )

            if not (is_evaluator or is_evaluated or is_admin or is_team_member):
                raise PermissionError("Нет прав для просмотра оценки")


class UpdateEvaluationInteractor:
    """Интерактор для обновления оценки"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        evaluation_uuid: UUID,
        update_data: EvaluationUpdate,
    ) -> Evaluation:
        """Обновить оценку"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            evaluation = await self._evaluation_repo.get_evaluation_with_relations(
                evaluation_uuid
            )

            if not actor:
                raise ValueError("Пользователь не найден")
            if not evaluation:
                raise ValueError("Оценка не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_update_evaluation(
                    actor, evaluation.task
                ):
                    raise PermissionError("Нет прав для обновления оценки")
            else:
                # Временная простая проверка
                is_evaluator = evaluation.evaluator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_evaluator or is_admin):
                    raise PermissionError(
                        "Только автор оценки или админ может обновлять оценку"
                    )

            # 3. Валидация изменений
            if update_data.score is not None:
                evaluation.score = update_data.score

            if update_data.comment is not None:
                evaluation.comment = update_data.comment

            # 4. Сохранить
            updated_evaluation = await self._evaluation_repo.update_evaluation(
                evaluation
            )
            await self._db_session.commit()
            return updated_evaluation

        except Exception:
            await self._db_session.rollback()
            raise


class DeleteEvaluationInteractor:
    """Интерактор для удаления оценки"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
        db_session: DBSession,
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator
        self._db_session = db_session

    async def __call__(
        self,
        actor_uuid: UUID,
        evaluation_uuid: UUID,
    ) -> bool:
        """Удалить оценку"""

        try:
            # 1. Найти участников
            actor = await self._user_repo.get_by_uuid(actor_uuid)
            evaluation = await self._evaluation_repo.get_evaluation_with_relations(
                evaluation_uuid
            )

            if not actor:
                raise ValueError("Пользователь не найден")
            if not evaluation:
                raise ValueError("Оценка не найдена")

            # 2. Проверить права доступа
            if self._permission_validator:
                if not await self._permission_validator.can_update_evaluation(
                    actor, evaluation.task
                ):
                    raise PermissionError("Нет прав для удаления оценки")
            else:
                # Временная простая проверка
                is_evaluator = evaluation.evaluator_uuid == actor.uuid
                is_admin = actor.role == RoleEnum.ADMIN

                if not (is_evaluator or is_admin):
                    raise PermissionError(
                        "Только автор оценки или админ может удалять оценку"
                    )

            # 3. Удалить оценку
            result = await self._evaluation_repo.delete_evaluation(evaluation_uuid)
            if result:
                await self._db_session.commit()
            return result

        except Exception:
            await self._db_session.rollback()
            raise


class QueryEvaluationsInteractor:
    """Интерактор для получения списка оценок"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        user_uuid: Optional[UUID] = None,
        evaluator_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        score: Optional[ScoresEnum] = None,
    ) -> List[Evaluation]:
        """Получить список оценок с фильтрацией"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Определить доступные оценки на основе роли
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только оценки своей команды
            final_team_uuid = actor.team_uuid
            if team_uuid and team_uuid != actor.team_uuid:
                raise PermissionError("Нет прав для просмотра оценок другой команды")
        else:
            # Админы и менеджеры могут указывать команду
            final_team_uuid = team_uuid

        # 3. Получить оценки
        if score is not None:
            evaluations = await self._evaluation_repo.get_evaluations_by_score(
                score=score,
                team_uuid=final_team_uuid,
                limit=limit,
            )
        elif user_uuid is not None:
            evaluations = await self._evaluation_repo.get_user_evaluations(
                user_uuid=user_uuid,
                limit=limit,
                offset=offset,
            )
        elif evaluator_uuid is not None:
            evaluations = await self._evaluation_repo.get_evaluations_by_evaluator(
                evaluator_uuid=evaluator_uuid,
                limit=limit,
                offset=offset,
            )
        elif final_team_uuid is not None:
            evaluations = await self._evaluation_repo.get_team_evaluations(
                team_uuid=final_team_uuid,
                limit=limit,
                offset=offset,
            )
        else:
            # Получаем последние оценки без фильтров
            evaluations = await self._evaluation_repo.get_recent_evaluations(
                limit=limit,
            )

        return evaluations


class GetUserEvaluationStatsInteractor:
    """Интерактор для получения статистики оценок пользователя"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        target_user_uuid: UUID,
    ) -> dict:
        """Получить статистику оценок пользователя"""

        # 1. Найти участников
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        target_user = await self._user_repo.get_by_uuid(target_user_uuid)

        if not actor:
            raise ValueError("Пользователь не найден")
        if not target_user:
            raise ValueError("Целевой пользователь не найден")

        # 2. Проверить права доступа
        if self._permission_validator:
            # TODO: Добавить метод can_view_user_evaluation_stats в PermissionValidator
            pass
        else:
            # Временная простая проверка
            is_self = target_user.uuid == actor.uuid
            is_admin = actor.role == RoleEnum.ADMIN
            is_manager = actor.role == RoleEnum.MANAGER
            is_same_team = actor.team_uuid == target_user.team_uuid

            if not (is_self or is_admin or (is_manager and is_same_team)):
                raise PermissionError("Нет прав для просмотра статистики оценок")

        # 3. Собрать статистику
        average_score = await self._evaluation_repo.calculate_user_average_score(
            target_user_uuid
        )
        score_distribution = await self._evaluation_repo.get_user_score_distribution(
            target_user_uuid
        )
        recent_count = await self._evaluation_repo.count_evaluations_by_period(
            user_uuid=target_user_uuid,
            days=30,
        )
        total_evaluations = sum(score_distribution.values())

        return {
            "user_uuid": str(target_user_uuid),
            "user_name": f"{target_user.name} {target_user.surname}",
            "average_score": round(average_score, 2) if average_score else 0.0,
            "total_evaluations": total_evaluations,
            "evaluations_last_30_days": recent_count,
            "score_distribution": {
                score.value: count for score, count in score_distribution.items()
            },
            "performance_level": self._get_performance_level(average_score)
            if average_score
            else "No evaluations",
        }

    def _get_performance_level(self, average_score: float) -> str:
        """Определить уровень производительности по средней оценке"""
        if average_score >= 4.5:
            return "Excellent"
        elif average_score >= 3.5:
            return "Good"
        elif average_score >= 2.5:
            return "Satisfactory"
        elif average_score >= 1.5:
            return "Needs Improvement"
        else:
            return "Poor"


class GetTeamEvaluationStatsInteractor:
    """Интерактор для получения статистики оценок команды"""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        user_repo: UserRepository,
        permission_validator: Optional[PermissionValidator],
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._user_repo = user_repo
        self._permission_validator = permission_validator

    async def __call__(
        self,
        actor_uuid: UUID,
        team_uuid: UUID,
    ) -> dict:
        """Получить статистику оценок команды"""

        # 1. Найти актора
        actor = await self._user_repo.get_by_uuid(actor_uuid)
        if not actor:
            raise ValueError("Пользователь не найден")

        # 2. Проверить права доступа
        if actor.role == RoleEnum.EMPLOYEE:
            # Сотрудники видят только статистику своей команды
            if team_uuid != actor.team_uuid:
                raise PermissionError(
                    "Нет прав для просмотра статистики другой команды"
                )

        # 3. Собрать статистику команды
        team_evaluations = await self._evaluation_repo.get_team_evaluations(
            team_uuid=team_uuid,
            limit=1000,  # Большой лимит для полной статистики
        )

        if not team_evaluations:
            return {
                "team_uuid": str(team_uuid),
                "total_evaluations": 0,
                "average_score": 0.0,
                "evaluations_last_30_days": 0,
                "score_distribution": {score.value: 0 for score in ScoresEnum},
            }

        # Вычисляем статистику
        score_values = {
            ScoresEnum.UNACCEPTABLE: 1,
            ScoresEnum.BAD: 2,
            ScoresEnum.SATISFACTORY: 3,
            ScoresEnum.GOOD: 4,
            ScoresEnum.GREAT: 5,
        }

        scores = [score_values[evaluation.score] for evaluation in team_evaluations]
        average_score = sum(scores) / len(scores)

        # Распределение оценок
        score_distribution = {score: 0 for score in ScoresEnum}
        for evaluation in team_evaluations:
            score_distribution[evaluation.score] += 1

        # Оценки за последние 30 дней
        recent_count = await self._evaluation_repo.count_evaluations_by_period(
            team_uuid=team_uuid,
            days=30,
        )

        return {
            "team_uuid": str(team_uuid),
            "total_evaluations": len(team_evaluations),
            "average_score": round(average_score, 2),
            "evaluations_last_30_days": recent_count,
            "score_distribution": {
                score.value: count for score, count in score_distribution.items()
            },
        }
