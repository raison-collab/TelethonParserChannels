import logging
import os
import string
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

BOT_URL = os.getenv('BOT_URL')

PHONE_NUMBER = os.getenv('PHONE_NUMBER')
PASSWORD = os.getenv('PASSWORD')

# чат в который будут писаться команды для редактирования каких-либо данных
COMMAND_CHAT = os.getenv('COMMAND_CHAT')

# настройка логирования
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Команды и их описание
commands = {
    '`/start`': '**Базовая информация о командах**\n',
    '`/chats`': '**Показать все ваши чаты**\n',
    '`/addChat <ID>`': '**Добавить чат для прослушивания.**\nСообщение отправлять в формате "/addChat <chat_id>", например "/addChat 12345" или вместо числового значения можно указать ссылку\n',
    '`/listeningChats`': '**Просмотреть список чатов, которые уже прослушиваются**\n',
    '`/removeChat <ID>`': '**Удалить чат из списка прослушиваемых**\n',
    '`/addKeyword <KEYWORD>`': '**Добавить ключевые слова.**\nНеобходимо ввести в формате "/addKeyword <KEYWORD>".\n**Важно**: <KEYWORD> - одно слово, на его основе построится список слов\n',
    '`/keywords`': 'Получить список ключевых слов\n',
    '`/editKeyword FROM_KEYWORD-TO_KEYWORD`': '**Обновить ключевое слово.**\n Необходимо ввести в формате "FROM_KEYWORD-TO_KEYWORD"\n**Важно**: FROM_KEYWORD - одно слово, которое вы хотите изменить\nTO_KEYWORD - одно слово на которое вы хотите изменить\n',
    '`/removeKeyword <KEYWORD>`': '**Удалить ключевое слово из спика.**\nНеобходимо ввести в формате "/addKeyword <KEYWORD>".\n**Важно**: <KEYWORD> - одно слово\n',
    '`/removeKeywords <KEYWORD>-<KEYWORD>`': '**Удалить ключевые слова из спика.**\nНеобходимо ввести в формате "/addKeyword <KEYWORD>-<KEYWORD>".\n**Важно**: <KEYWORD> - одно слово, слова разделены символом "-"\n',
    '`/allThemes`': '**Файл со списком тем**\n',
    '`/addTheme <THEME_NAME>-<KEYWORD>-<KEYWORD>`': '**Добавить тему**\nНеобходимо ввести в формате "<THEME_NAME>-<KEYWORD>-<KEYWORD>", где\nTHEME_NAME - название темы, которую хотите добавить\nKEYWORD - ключево слово, которое должно быть в этой теме\n**Важно** ключевое слово должно быть в базе данных иначе оно не будет включено в тему\n',
    '`/addKeyWordsToTheme <THEME_NAME>-<KEYWORD>-<KEYWORD>`': '**Добавить ключевые слова в тему**\nНеобходимо ввести в формате "<THEME_NAME>-<KEYWORD>-<KEYWORD>", где\nTHEME_NAME - название темы, которую хотите добавить\nKEYWORD - ключево слово, которое должно быть в этой теме\n**Важно** ключевое слово должно быть в базе данных иначе оно не будет включено в тему\n',
    '`/removeKeywordsFromTheme <THEME_NAME>-<KEYWORD>-<KEYWORD>`': '**Удалить ключевые слова из темы**\nНеобходимо ввести в формате "<THEME_NAME>-<KEYWORD>-<KEYWORD>", где\nTHEME_NAME - название темы, которую хотите добавить\nKEYWORD - ключево слово, которое должно быть в этой теме\n**Важно** ключевое слово должно быть в базе данных иначе оно не будет включено в тему\n',
    '`/removeThemes <THEME_NAME>-<THEME_NAME>`': '**Удалить тему/темы**\nНеобходимо ввести в формате "<THEME_NAME>-<THEME_NAME>", где\nTHEME_NAME - название темы, которую хотите удалить\n**Важно** темы должны быть в базе данных\n',
    '`/followThemes <THEME_NAME>-<THEME_NAME>`': '**Начать отслеживать тему/темы**\nНеобходимо ввести в формате "<THEME_NAME>-<THEME_NAME>", где\nTHEME_NAME - название темы, которую хотите отслеживать\n**Важно** темы должны быть в базе данных\n',
    '`/unfollowThemes <THEME_NAME>-<THEME_NAME>`': '**Прекратить отслеживать тему/темы**\nНеобходимо ввести в формате "<THEME_NAME>-<THEME_NAME>", где\nTHEME_NAME - название темы, которую больше не хотите отслеживать\n**Важно** темы должны быть в базе данных\n',
}

client = TelegramClient('parser', API_ID, API_HASH)

# переменные для названия файлов, в которых будет храниться соответсвующая инфа
LISTENING_CHATS_FILENAME = "listen_chats.txt"
ALL_CHATS_FILENAME = "all_chats.txt"
KEYWORDS_FILENAME = "keywords.txt"
THEMES_FILENAME = "themes.txt"

IGNORE_SYMBOLS = string.punctuation

UPLOAD_FOLDER = os.getcwd() + "\\media"

SQLITE_FILENAME = "database.db"
SQLITE_DATABASE_PATH = f"./{SQLITE_FILENAME}"
SQLITE_DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_DATABASE_PATH}"

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USERNAME = os.getenv("PG_USERNAME")
PG_PASSWORD = os.getenv("PG_PASSWORD")
POSTGRES_DATABASE_URL = f"postgresql+asyncpg://{PG_USERNAME}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"


class LoggerTags(Enum):
    COMMAND = '[Command]'
    HANDLER = '[Handler]'
    DATABASE = '[Database]'
    SCHEDULER = '[Scheduler]'


class MessageFiletypes(Enum):
    PHOTO = 'photo'
    DOCUMENT = 'document'


engine = create_async_engine(SQLITE_DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)

scheduler = AsyncIOScheduler()
