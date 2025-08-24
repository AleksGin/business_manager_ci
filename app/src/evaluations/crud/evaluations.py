from datetime import datetime, timedelta
from typing import (
    List,
    Optional,
)
from uuid import UUID

from sqlalchemy import (
    and_,
    desc,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.evaluations.interfaces import EvaluationRepository
from src.evaluations.models import Evaluation, ScoresEnum
from src.tasks.models import Task


class EvaluationCRUD(EvaluationRepository):
    """Имплементация EvaluationRepository"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """Создать новую оценку"""
        self._session.add(evaluation)
        await self._session.flush()
        await self._session.refresh(evaluation)
        return evaluation

    async def get_by_uuid(self, evaluation_uuid: UUID) -> Optional[Evaluation]:
        """Получить оценку по UUID"""
        stmt = select(Evaluation).where(Evaluation.uuid == evaluation_uuid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_task_uuid(self, task_uuid: UUID) -> Optional[Evaluation]:
        """Получить оценку по UUID задачи"""
        stmt = select(Evaluation).where(Evaluation.task_uuid == task_uuid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """Обновить оценку"""
        await self._session.flush()
        await self._session.refresh(evaluation)
        return evaluation

    async def delete_evaluation(self, evaluation_uuid: UUID) -> bool:
        """Удалить оценку"""
        evaluation = await self.get_by_uuid(evaluation_uuid)

        if not evaluation:
            return False

        await self._session.delete(evaluation)
        await self._session.flush()
        return True

    async def get_user_evaluations(
        self,
        user_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evaluation]:
        """Получить оценки пользователя (полученные им)"""
        stmt = select(Evaluation).where(Evaluation.evaluated_user_uuid == user_uuid)
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(desc(Evaluation.created_at))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_evaluations_by_evaluator(
        self,
        evaluator_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evaluation]:
        """Получить оценки, поставленные конкретным оценщиком"""
        stmt = select(Evaluation).where(Evaluation.evaluator_uuid == evaluator_uuid)
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(desc(Evaluation.created_at))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_evaluations(
        self,
        team_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evaluation]:
        """Получить оценки команды (через задачи команды)"""
        # Соединяем Evaluation с Task чтобы фильтровать по команде
        stmt = (
            select(Evaluation)
            .join(Task, Evaluation.task_uuid == Task.uuid)
            .where(Task.team_uuid == team_uuid)
        )
        stmt = stmt.offset(offset).limit(limit)
        stmt = stmt.order_by(desc(Evaluation.created_at))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_evaluations_by_score(
        self,
        score: ScoresEnum,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Evaluation]:
        """Получить оценки по определенному баллу"""
        stmt = select(Evaluation).where(Evaluation.score == score)

        if team_uuid:
            stmt = stmt.join(Task, Evaluation.task_uuid == Task.uuid)
            stmt = stmt.where(Task.team_uuid == team_uuid)

        stmt = stmt.limit(limit)
        stmt = stmt.order_by(desc(Evaluation.created_at))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_evaluation_with_relations(
        self,
        evaluation_uuid: UUID,
    ) -> Optional[Evaluation]:
        """Получить оценку с загруженными связями"""
        stmt = select(Evaluation).where(Evaluation.uuid == evaluation_uuid)
        stmt = stmt.options(
            selectinload(Evaluation.task),  # Загружаем задачу
            selectinload(Evaluation.evaluator),  # Загружаем оценивающего
            selectinload(Evaluation.evaluated_user),  # Загружаем оцениваемого
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def calculate_user_average_score(self, user_uuid: UUID) -> Optional[float]:
        """Вычислить среднюю оценку пользователя"""
        # Преобразуем ScoresEnum в числовые значения
        score_values = {
            ScoresEnum.UNACCEPTABLE: 1,
            ScoresEnum.BAD: 2,
            ScoresEnum.SATISFACTORY: 3,
            ScoresEnum.GOOD: 4,
            ScoresEnum.GREAT: 5,
        }

        # Получаем все оценки пользователя
        stmt = select(Evaluation.score).where(
            Evaluation.evaluated_user_uuid == user_uuid
        )
        result = await self._session.execute(stmt)
        scores = result.scalars().all()

        if not scores:
            return None

        # Вычисляем среднее
        numeric_scores = [score_values[score] for score in scores]
        return sum(numeric_scores) / len(numeric_scores)

    async def get_user_score_distribution(
        self,
        user_uuid: UUID,
    ) -> dict[ScoresEnum, int]:
        """Получить распределение оценок пользователя по типам"""
        stmt = (
            select(Evaluation.score, func.count(Evaluation.uuid))
            .where(Evaluation.evaluated_user_uuid == user_uuid)
            .group_by(Evaluation.score)
        )

        result = await self._session.execute(stmt)

        # Инициализируем все типы оценок нулями
        distribution = {score: 0 for score in ScoresEnum}

        # Заполняем реальными значениями
        for score, count in result.all():
            distribution[score] = count

        return distribution

    async def count_evaluations_by_period(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        days: int = 30,
    ) -> int:
        """Подсчитать количество оценок за период"""
        since_date = datetime.now() - timedelta(days=days)

        stmt = select(func.count(Evaluation.uuid)).where(
            Evaluation.created_at >= since_date
        )

        if user_uuid:
            stmt = stmt.where(Evaluation.evaluated_user_uuid == user_uuid)

        if team_uuid:
            stmt = stmt.join(Task, Evaluation.task_uuid == Task.uuid)
            stmt = stmt.where(Task.team_uuid == team_uuid)

        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_recent_evaluations(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[Evaluation]:
        """Получить последние оценки"""
        stmt = select(Evaluation)

        conditions = []

        if user_uuid:
            conditions.append(Evaluation.evaluated_user_uuid == user_uuid)

        if team_uuid:
            stmt = stmt.join(Task, Evaluation.task_uuid == Task.uuid)
            conditions.append(Task.team_uuid == team_uuid)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.limit(limit)
        stmt = stmt.order_by(desc(Evaluation.created_at))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
