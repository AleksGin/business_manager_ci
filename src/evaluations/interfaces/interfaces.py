from typing import (
    List,
    Optional,
    Protocol,
)
from uuid import UUID

from evaluations.models import (
    Evaluation,
    ScoresEnum,
)


class EvaluationRepository(Protocol):
    """Интерфейс для работы с оценками в хранилище данных"""

    async def create_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """Создать новую оценку"""
        ...

    async def get_by_uuid(self, evaluation_uuid: UUID) -> Optional[Evaluation]:
        """Получить оценку по UUID"""
        ...

    async def get_by_task_uuid(self, task_uuid: UUID) -> Optional[Evaluation]:
        """Получить оценку по UUID задачи"""
        ...

    async def update_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """Обновить оценку"""
        ...

    async def delete_evaluation(self, evaluation_uuid: UUID) -> bool:
        """Удалить оценку"""
        ...

    async def get_user_evaluations(
        self,
        user_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evaluation]:
        """Получить оценки пользователя (полученные им)"""
        ...

    async def get_evaluations_by_evaluator(
        self,
        evaluator_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evaluation]:
        """Получить оценки, поставленные конкретным оценщиком"""
        ...

    async def get_team_evaluations(
        self,
        team_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evaluation]:
        """Получить оценки команды (через задачи команды)"""
        ...

    async def get_evaluations_by_score(
        self,
        score: ScoresEnum,
        team_uuid: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Evaluation]:
        """Получить оценки по определенному баллу"""
        ...

    async def get_evaluation_with_relations(
        self, evaluation_uuid: UUID
    ) -> Optional[Evaluation]:
        """Получить оценку с загруженными связями (task, evaluator, evaluated_user)"""
        ...

    async def calculate_user_average_score(self, user_uuid: UUID) -> Optional[float]:
        """Вычислить среднюю оценку пользователя"""
        ...

    async def get_user_score_distribution(
        self,
        user_uuid: UUID,
    ) -> dict[ScoresEnum, int]:
        """Получить распределение оценок пользователя по типам"""
        ...

    async def count_evaluations_by_period(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        days: int = 30,
    ) -> int:
        """Подсчитать количество оценок за период"""
        ...

    async def get_recent_evaluations(
        self,
        user_uuid: Optional[UUID] = None,
        team_uuid: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[Evaluation]:
        """Получить последние оценки"""
        ...
