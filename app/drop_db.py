import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# сюда подставьте ваш реальный URL с ssl=require
DATABASE_URL = "postgresql+asyncpg://root:root@ai-edward0076.db-msk0.amvera.tech:5432/root?ssl=require"


async def clear_chats_table():
    """Очистка только таблицы chats"""
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"ssl": "require"},
        echo=True  # включаем логирование для отладки
    )

    async with engine.connect() as conn:
        try:
            # Начинаем транзакцию
            await conn.begin()

            print("🚀 Начинаю очистку таблицы chats...")

            # 1. Проверяем существование таблицы chats
            result = await conn.execute(text("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_name = 'chats'
                AND table_schema NOT IN ('pg_catalog', 'information_schema');
            """))

            chat_table = result.fetchone()

            if not chat_table:
                print("❌ Таблица 'chats' не найдена в базе данных.")
                return

            schema, table = chat_table
            print(f"📋 Найдена таблица: {schema}.{table}")

            # 2. Очищаем только таблицу chats
            try:
                # Используем TRUNCATE для быстрой очистки
                await conn.execute(text(f'TRUNCATE TABLE "{schema}"."{table}" RESTART IDENTITY CASCADE;'))
                print(f"✅ Таблица {schema}.{table} успешно очищена (TRUNCATE)")
            except Exception as e:
                print(f"⚠️  Не удалось очистить TRUNCATE: {e}")
                # Пробуем DELETE если TRUNCATE не работает
                try:
                    await conn.execute(text(f'DELETE FROM "{schema}"."{table}";'))
                    print(f"✅ Таблица {schema}.{table} очищена (DELETE)")
                except Exception as e2:
                    print(f"❌ Не удалось очистить таблицу: {e2}")
                    raise

            # 3. Сбрасываем sequence для chats если он существует
            try:
                await conn.execute(text(f'ALTER SEQUENCE IF EXISTS "{schema}".chats_id_seq RESTART WITH 1;'))
                print("✅ Sequence сброшен (если существовал)")
            except Exception as e:
                print(f"⚠️  Не удалось сбросить sequence: {e}")

            # Коммитим транзакцию
            await conn.commit()
            print("🎉 Таблица chats полностью очищена!")

        except Exception as e:
            # Откатываем транзакцию в случае ошибки
            await conn.rollback()
            print(f"❌ Ошибка при очистке таблицы chats: {e}")
            raise

        finally:
            await conn.close()

    await engine.dispose()


async def check_chats_table():
    """Проверка таблицы chats"""
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"ssl": "require"}
    )
    async with engine.connect() as conn:
        # Проверяем существование таблицы
        result = await conn.execute(text("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_name = 'chats'
            AND table_schema NOT IN ('pg_catalog', 'information_schema');
        """))

        table_info = result.fetchone()
        if not table_info:
            print("❌ Таблица 'chats' не найдена.")
            return

        schema, table, table_type = table_info
        print(f"📋 Таблица найдена: {schema}.{table} ({table_type})")

        # Проверяем количество записей
        count_result = await conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}";'))
        count = count_result.scalar()
        print(f"📊 Количество записей в chats: {count}")

    await engine.dispose()


async def delete_chats_by_ids():
    """Удаление чатов по ID (альтернативный метод через DAO)"""
    from app.database import async_session_maker
    from app.chat_gpt.dao import ChatDAO

    async with async_session_maker() as session:
        deleted_count = 0
        error_count = 0

        # Диапазон ID для удаления (настройте по необходимости)
        for i in range(1, 1000):  # Увеличил диапазон на всякий случай
            try:
                result = await ChatDAO.delete(session, id=i)
                if result:
                    deleted_count += 1
                    print(f"✅ Чат с ID {i} удален")
                else:
                    # Если чат не найден, пропускаем
                    pass

            except Exception as e:
                error_count += 1
                print(f"❌ Ошибка при удалении чата {i}: {e}")

        try:
            await session.commit()
            print(f"🎉 Удалено чатов: {deleted_count}, ошибок: {error_count}")
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка коммита: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Утилита для работы с таблицей chats")
    parser.add_argument('--action', choices=['check', 'clear', 'delete-ids', 'count'],
                        default='check',
                        help='Действие: check - проверить таблицу, clear - очистить таблицу, delete-ids - удалить по ID, count - посчитать записи')

    args = parser.parse_args()

    if args.action == 'check':
        asyncio.run(check_chats_table())
    elif args.action == 'clear':
        # Запрашиваем подтверждение для очистки
        confirm = input("⚠️  ВНИМАНИЕ: Это полностью очистит таблицу chats! Продолжить? (y/N): ")
        if confirm.lower() == 'y':
            asyncio.run(clear_chats_table())
        else:
            print("❌ Очистка отменена.")
    elif args.action == 'delete-ids':
        confirm = input("⚠️  Удалить чаты по ID? (y/N): ")
        if confirm.lower() == 'y':
            asyncio.run(delete_chats_by_ids())
        else:
            print("❌ Удаление отменено.")
    elif args.action == 'count':
        asyncio.run(check_chats_table())