import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from fatcules.config import Settings
from fatcules.db import EntryRepository
from fatcules.handlers import router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    repo = EntryRepository(settings.database_path)
    await repo.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    bot.repo = repo  # type: ignore[attr-defined]
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
