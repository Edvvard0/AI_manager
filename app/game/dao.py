# from pydantic import BaseModel
# from sqlalchemy import select, desc, func
# from sqlalchemy.exc import SQLAlchemyError
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import Base
# from app.game.models import User
#
#
# class UserDAO(Base):
#     model = User
#
#     @classmethod
#     async def find_one_or_none(cls, session: AsyncSession, filters: BaseModel):
#         # Найти одну запись по фильтрам
#         filter_dict = filters.model_dump(exclude_unset=True)
#         try:
#             query = select(cls.model).filter_by(**filter_dict)
#             result = await session.execute(query)
#             record = result.scalar_one_or_none()
#             return record
#         except SQLAlchemyError as e:
#             raise
#
#     @classmethod
#     async def add(cls, session: AsyncSession, values: BaseModel):
#         # Добавить одну запись
#         values_dict = values.model_dump(exclude_unset=True)
#         new_instance = cls.model(**values_dict)
#         session.add(new_instance)
#         try:
#             await session.commit()
#         except SQLAlchemyError as e:
#             await session.rollback()
#             raise e
#         return new_instance
#
#     @classmethod
#     async def get_top_scores(cls, session: AsyncSession, limit: int = 20):
#         """
#         Получить топ рекордов, отсортированных от самого высокого к низкому, с добавлением номера позиции.
#         """
#         try:
#             query = (
#                 select(cls.model.telegram_id, cls.model.first_name, cls.model.best_score)
#                 .order_by(desc(cls.model.best_score))
#                 .limit(limit)
#             )
#             result = await session.execute(query)
#             records = result.fetchall()
#
#             # Добавление поля `rank` для нумерации позиций
#             ranked_records = [
#                 {"rank": index + 1, "telegram_id": record.telegram_id, "first_name": record.first_name,
#                  "best_score": record.best_score}
#                 for index, record in enumerate(records)
#             ]
#
#             return ranked_records
#         except SQLAlchemyError as e:
#             raise e
#
#     @classmethod
#     async def get_user_rank(cls, session: AsyncSession, telegram_id: int):
#         """
#         Получить место пользователя по telegram_id в списке рекордов.
#         Возвращает словарь с полями rank и best_score.
#         """
#         try:
#             # Подзапрос для вычисления рангов на основе best_score
#             rank_subquery = (
#                 select(
#                     cls.model.telegram_id,
#                     cls.model.best_score,
#                     func.rank().over(order_by=desc(cls.model.best_score)).label("rank")
#                 )
#                 .order_by(desc(cls.model.best_score))
#                 .subquery()
#             )
#
#             # Запрос для получения ранга и best_score конкретного пользователя
#             query = select(rank_subquery.c.rank, rank_subquery.c.best_score).where(
#                 rank_subquery.c.telegram_id == telegram_id
#             )
#             result = await session.execute(query)
#             rank_row = result.fetchone()
#
#             # Возвращаем словарь с рангом и лучшим результатом
#             return {"rank": rank_row.rank, "best_score": rank_row.best_score} if rank_row else None
#         except SQLAlchemyError as e:
#             raise e
