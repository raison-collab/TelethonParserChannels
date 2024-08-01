import asyncio
import sqlite3
from typing import Callable

import asyncpg
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import MetaData
from telethon import events
from telethon.errors import FloodWaitError

from chats import ChatsHandler
from commands import CommandsHandler
from config import *
from data import Base
from data.db_manager import DBManager
from scheduler_manager import ThemeSchedulerManager

db_manager = DBManager()
chats_handler = ChatsHandler(client)
commands_handler = CommandsHandler(client, chats_handler)
theme_scheduler = ThemeSchedulerManager()

commands: dict[str, Callable] = {
    '/start': commands_handler.start_command,
    '/chats': commands_handler.chats_command,
    '/addChat': commands_handler.add_chat_command,
    '/listeningChats': commands_handler.listening_chats_command,
    '/removeChat': commands_handler.remove_chat_command,
    '/addKeyword': commands_handler.add_keyword_command,
    '/removeKeyword': commands_handler.remove_keyword_command,
    '/removeKeywords': commands_handler.remove_keywords_command,
    '/keywords': commands_handler.keywords_command,
    '/editKeyword': commands_handler.edit_keyword_command,
    '/allThemes': commands_handler.all_themes_command,
    '/addTheme': commands_handler.add_theme_command,
    '/addKeyWordsToTheme': commands_handler.add_keyword_to_theme_command,
    '/removeKeywordsFromTheme': commands_handler.remove_keywords_from_theme_command,
    '/removeThemes': commands_handler.remove_themes_command,
    '/followThemes': commands_handler.follow_themes_command,
    '/unfollowThemes': commands_handler.unfollow_themes_command,
    '/changeIntervalTheme': commands_handler.change_interval_theme,
}


def check_file(file_name: str):
    if not os.path.isfile(file_name):
        with open(file_name, 'w') as _:
            pass
        logger.info(f"Added file {file_name}")


def create_directories():
    logger.info("Creating directories")
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(f"{UPLOAD_FOLDER}/{MessageFiletypes.DOCUMENT.value}", exist_ok=True)
    os.makedirs(f"{UPLOAD_FOLDER}/{MessageFiletypes.PHOTO.value}", exist_ok=True)


def create_database(db_path: str):
    # Попытка соединения с базой данных, которое приведет к ее созданию, если она еще не существует
    conn = sqlite3.connect(db_path)
    conn.close()
    logger.success("Database created successfully")


async def create_tables(*metadata: MetaData):
    async with engine.begin() as conn:
        for data in metadata:
            await conn.run_sync(data.create_all)
    logger.success("Tables created successfully")


async def try_to_connect_postgres():
    try:
        connection = await asyncpg.connect(
            user=PG_USERNAME,
            password=PG_PASSWORD,
            database=PG_DATABASE,
            host=PG_HOST,
            port=PG_PORT
        )
        logger.success("Подключение к базе данных успешно установлено")

        await connection.close()
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")


async def update_channels():
    logger.info(f"{LoggerTags.SCHEDULER.value} Update channels")
    try:
        new_chats = await chats_handler.listening_chats_list()
        client.remove_event_handler(chats_handler.normal_handler)
        client.add_event_handler(
            chats_handler.normal_handler,
            events.NewMessage(chats=new_chats)
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении каналов: {e}")


async def run_themes_scheduler():
    logger.debug(f"{LoggerTags.SCHEDULER.value} start themes scheduler")
    themes = await db_manager.themes.all_themes()
    _ = [await theme_scheduler.add_new_theme_job(theme.theme_name, theme.interval) for theme in themes if theme.is_following]


async def run_scheduled_tasks():
    logger.info(f"{LoggerTags.SCHEDULER.value} Run scheduled tasks")
    await run_themes_scheduler()


async def startup():
    await add_command_chat(COMMAND_CHAT)

    # await try_to_connect_postgres()

    scheduler.add_job(update_channels, IntervalTrigger(seconds=15), id="update_channels")
    scheduler.start()

    # для создания файлов
    check_file(ALL_CHATS_FILENAME)
    check_file(LISTENING_CHATS_FILENAME)
    check_file(KEYWORDS_FILENAME)

    create_directories()

    create_database(SQLITE_DATABASE_PATH)
    await create_tables(Base.metadata)

    client.add_event_handler(
        chats_handler.normal_handler,
        events.NewMessage(
            chats=await chats_handler.listening_chats_list()
        )
    )

    await run_scheduled_tasks()

    logger.success('Telethon started')
    logger.info(f"Set moderation chat - {BOT_URL}")


async def add_command_chat(chat: str):
    client.add_event_handler(commands_handler, events.NewMessage(chats=(chat,), pattern=r'^/\w+(?:\s[\w+-]+|\s\S+)?$'))
    logger.info(f"Add chat for commands - {COMMAND_CHAT}")


async def commands_handler(event: events.NewMessage.Event):
    """
    Обработчик команд
    :param event: событие
    """
    msg = event.message.to_dict()['message']

    command = msg.split(' ')[0]

    print(f"{command=}")

    if command not in commands.keys():
        await event.reply("**Нет** такой команды")
        return

    logger.info(f"Command {command=}")

    await commands[command](event)


async def main():
    await startup()

    if PASSWORD:
        await client.start(phone=PHONE_NUMBER, password=PASSWORD)
    else:
        await client.start(phone=PHONE_NUMBER)

    await client.run_until_disconnected()

try:
    client.loop.run_until_complete(main())
except Exception as e:
    logger.error("e")
