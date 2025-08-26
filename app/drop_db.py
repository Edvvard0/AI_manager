import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# сюда подставьте ваш реальный URL с ssl=require
DATABASE_URL = "postgresql+asyncpg://root:root@ai-edward0076.db-msk0.amvera.tech:5432/root?ssl=require"


async def check_tables():
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"ssl": "require"}
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name;
        """))
        rows = result.fetchall()
        if not rows:
            print("В базе нет пользовательских таблиц.")
        else:
            print("Найдены таблицы:")
            for schema, table in rows:
                print(f"{schema}.{table}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_tables())