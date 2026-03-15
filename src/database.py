import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Local dev: direct connection string
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
else:
    # Cloud Run: use Cloud SQL connector with IAM auth
    from google.cloud.sql.connector import create_async_connector

    INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "kerjasama-dev:europe-west2:kerjasama-db")
    DB_NAME = os.getenv("DB_NAME", "kerjasama")
    DB_USER = os.getenv("DB_USER", "kerjasama-chat-api@kerjasama-dev.iam")

    _connector = None

    async def getconn():
        global _connector
        if _connector is None:
            _connector = await create_async_connector()
        conn = await _connector.connect_async(
            INSTANCE_CONNECTION_NAME,
            "asyncpg",
            user=DB_USER,
            db=DB_NAME,
            enable_iam_auth=True,
        )
        return conn

    engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=getconn,
        pool_pre_ping=True,
        echo=False,
    )

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
