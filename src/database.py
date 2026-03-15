import os

from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "kerjasama-dev:europe-west2:kerjasama-db")
DB_NAME = os.getenv("DB_NAME", "kerjasama")
DB_USER = os.getenv("DB_USER", "kerjasama-chat-api@kerjasama-dev.iam")

connector = Connector()


async def getconn():
    conn = await connector.connect_async(
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
