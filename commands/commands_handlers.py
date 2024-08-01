from typing import Callable

from loguru import logger
from sqlalchemy.exc import IntegrityError
from telethon import TelegramClient, events, types

from chats.chats_handlers import ChatsHandler
from config import commands, ALL_CHATS_FILENAME, LISTENING_CHATS_FILENAME, KEYWORDS_FILENAME, LoggerTags, \
    THEMES_FILENAME

from keywords import KeywordsHandler, ThemesHandler

from functools import wraps


def check_args_count(expected_count: int):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, event: events.NewMessage.Event, *args, **kwargs):
            msg = event.message.to_dict()['message']
            if len(msg.split()) != expected_count:
                await event.reply(f"**Ошибка! Проверьте формат ввода данных**")
                return
            return await func(self, event, *args, **kwargs)

        return wrapper

    return decorator


# todo написать еще один декоратор для валидации данных word-word

class CommandsHandler:
    def __init__(self,
                 client: TelegramClient,
                 chats_handler: ChatsHandler):

        self.client = client
        self.ch = chats_handler
        self.kh = KeywordsHandler()
        self.themes = ThemesHandler()

    async def start_command(self, event: events.NewMessage.Event):
        st = ''

        for command in commands:
            st += f'{command} - {commands[command]}\n'

        await event.reply(f'**Список комманд:**\n{st}')

    async def chats_command(self, event: events.NewMessage.Event):
        with open(ALL_CHATS_FILENAME, 'w', encoding='utf8') as f:
            chats = '\n'.join([f'{chat.title} - {chat.entity.id}' async for chat in self.client.iter_dialogs() if
                               isinstance(chat.entity, types.Channel)])
            f.write(chats)

        await self.client.send_file(event.chat_id, ALL_CHATS_FILENAME)

    @check_args_count(2)
    async def add_chat_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        try:
            if msg.split()[1].isdigit():
                await self.ch.add_chat(int(msg.split()[1]))
            else:
                await self.ch.add_chat(msg.split()[1])
        except KeyError as e:
            await event.reply(f'Ошибка: {e}')
            return

        await event.reply(f"Чат {msg.split()[1]} **добавлен**")

    async def listening_chats_command(self, event: events.NewMessage.Event):
        logger.info(f"{LoggerTags.COMMAND.value} Listening chats command")

        listening_chats = await self.ch.listening_chats_list()

        st = '\n'.join([f'{chat.title} - {chat.entity.id}' async for chat in self.client.iter_dialogs() if
                        chat.entity.id in listening_chats])

        with open(LISTENING_CHATS_FILENAME, 'w', encoding='utf8') as f:
            f.write(st)

        await self.client.send_file(event.chat_id, LISTENING_CHATS_FILENAME)

    @check_args_count(2)
    async def remove_chat_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        try:
            if msg.split()[1].isdigit():
                await self.ch.remove_chat(int(msg.split()[1]))
            else:
                await self.ch.remove_chat(msg.split()[1])
        except KeyError as e:
            await event.reply(f"Ошибка: {e}")
            return

        await event.reply(f"Чат {msg.split()[1]} **удален** из списка прослуиваемых")

    @check_args_count(2)
    async def add_keyword_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        if msg.split()[1].isdigit():
            await event.reply("Ключевое слово не может быть числом")
            return

        keywords = await self.kh.add_keyword(msg.split()[1])
        await event.reply(f'**Были добавлены следующие слова:**\n{"-".join(keywords)}')

    @check_args_count(2)
    async def remove_keyword_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        if msg.split()[1].isdigit():
            await event.reply("Ключевое слово не может быть числом")
            return

        try:
            await self.kh.remove_keyword(msg.split()[1])
            await event.reply(f"Ключевое слово '{msg.split()[1]}' **удалено**")
        except KeyError as e:
            await event.reply(f"**Ошибка**: {e}")

    @check_args_count(2)
    async def remove_keywords_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        if msg.split()[1].isdigit():
            await event.reply("Ключевое слово не может быть числом")
            return

        keywords = [el.strip() for el in msg.split()[1].split('-')]

        await self.kh.remove_keywords(keywords)
        await event.reply("Данные ключевые слова **удалены**")

    @check_args_count(2)
    async def edit_keyword_command(self, event: events.NewMessage.Event):
        logger.info(f"{LoggerTags.COMMAND.value} Command for editing keyword")
        msg = event.message.to_dict()['message']

        if msg.split()[1].isdigit():
            await event.reply("Ключевое слово не может быть числом")
            return

        command_data = msg.split()[1].split('-')

        if len(command_data) != 2:
            await event.reply("Проверьте правильность команды и ее аргументов")
            return

        from_keyword = command_data[0]
        to_keyword = command_data[1]

        try:
            await self.kh.edit_keyword(from_keyword, to_keyword)
        except ValueError as e:
            await event.reply(f"**Ошибка!** {e}")
            return
        except IntegrityError as e:
            logger.error(e)
            await event.reply("**Ошибка!** В этот раз не получилось обновить слово, возможно вы ошиблись")
            return

        await event.reply(f"Ваше слово успешно **обновлено**")

    @check_args_count(1)
    async def keywords_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        words = await self.kh.get_keywords()

        # заполняем файл с ключевыми словами
        with open(KEYWORDS_FILENAME, 'w', encoding='utf8') as f:
            f.write('-'.join(list(words)))

        await self.client.send_file(event.chat_id, KEYWORDS_FILENAME)

    async def all_themes_command(self, event: events.NewMessage.Event):
        logger.info(LoggerTags.COMMAND.value + " AllThemes command")
        themes = await self.themes.all_themes()

        st = ''

        for theme in themes:
            status = '✅' if theme.is_following else '❌'
            st += f"{theme.theme_name} - {status} - |{'-'.join([el.word for el in theme.keywords])}|\n\n"

        with open(THEMES_FILENAME, 'w', encoding='utf8') as f:
            f.write(st)

        await self.client.send_file(event.chat_id, THEMES_FILENAME)

    # todo refactor methods. Write method with validate args and validate keywords
    @check_args_count(2)
    async def add_theme_command(self, event: events.NewMessage.Event):
        # todo обновить описание добавления тем
        # todo добавить команду на обновление интервала темы
        msg = event.message.to_dict()['message']

        command_data = msg.split()[1]

        if len(command_data.split('-')) < 3:
            await event.reply('Проверьте правильность ввода информации, возможно вы ошиблись с форматом')
            return

        theme_name = command_data.split('-')[0].replace('+', ' ')
        interval = command_data.split('-')[1]
        # period = command_data.split('-')[2]
        keywords = list(set(command_data.split('-')[2:]))

        if not interval.isdigit():
            await event.reply(f"Интервал должен быть целым числом")
            return

        logger.info(LoggerTags.COMMAND.value + f"Add with {theme_name=} and {keywords=}")

        keywords_db = []
        errors_words = []

        for word in keywords:
            w = await self.kh.get_keyword(word)
            if w is None:
                errors_words.append(word)
                continue
            keywords_db.append(w)
        try:
            await self.themes.add_theme(theme_name, interval, keywords_db)
        except IntegrityError as e:
            logger.error(e)
            await event.reply("**Ошибка!** Возможно тема с таким именем уже есть")
            return

        if errors_words:
            await event.reply(
                f"Были добавлены слова, кроме этих\n\n{'-'.join(errors_words)}\n\nТак как их **нет в базе данных**")
        else:
            await event.reply(f"**Были добавлены все слова**")

    @check_args_count(2)
    async def add_keyword_to_theme_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        command_data = msg.split()[1]

        theme_name = command_data.split('-')[0].replace('+', ' ')
        keywords = list(set(command_data.split('-')[1:]))

        logger.info(LoggerTags.COMMAND.value + f" Edit with {theme_name=} and {keywords=}")

        if len(command_data.split('-')) < 2:
            await event.reply('Проверьте правильность ввода информации, возможно вы ошиблись с форматом')
            return

        keywords_db = []
        errors_words = []

        for word in keywords:
            w = await self.kh.get_keyword(word)
            if w is None:
                errors_words.append(word)
                continue
            keywords_db.append(w)

        try:
            await self.themes.add_keyword_to_theme(theme_name, keywords_db)
        except KeyError as e:
            logger.error(e)
            await event.reply(f"**Ошибка!** {e}")
            return
        except IntegrityError as e:
            logger.error(e)
            await event.reply(f"**Ошибка!** Ошибка с обновленим ваших слов в теме")
            return

        if errors_words:
            await event.reply(
                f"Были добавлены слова, кроме этих\n\n{'-'.join(errors_words)}\n\nТак как их **нет в базе данных**")
        else:
            await event.reply(f"**Были добавлены все слова**")

    async def remove_keywords_from_theme_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        command_data = msg.split()
        if len(command_data) != 2:
            await event.reply(f"Вы **ошиблись** в форматом")
            return

        command_data = command_data[1]

        theme_name = command_data.split('-')[0].replace('+', ' ')
        keywords = list(set(command_data.split('-')[1:]))

        logger.info(LoggerTags.COMMAND.value + f" Remove from {theme_name=} {keywords=}")

        if len(command_data.split('-')) < 2:
            await event.reply('Проверьте правильность ввода информации, возможно вы ошиблись с форматом')
            return

        keywords_db = []
        errors_words = []

        for word in keywords:
            w = await self.kh.get_keyword(word)
            if w is None:
                errors_words.append(word)
                continue
            keywords_db.append(w)

        try:
            await self.themes.remove_keywords_from_theme(theme_name, keywords_db)
        except IntegrityError as e:
            logger.error(e)
            await event.reply(f"**Ошибка!** Ошибка с удалением ваших слов в теме")
            return

        if errors_words:
            await event.reply(
                f"Были удалены слова, кроме этих\n\n{'-'.join(errors_words)}\n\nТак как их **нет в базе данных**")
        else:
            await event.reply(f"**Были удалены все слова**")

    async def remove_themes_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        command_data = msg.split()
        if len(command_data) != 2:
            await event.reply(f"Вы **ошиблись** в форматом")
            return

        command_data = command_data[1]

        themes_names = list(set(command_data.split('-').replace('+', ' ')))

        logger.info(LoggerTags.COMMAND.value + f" Remove {themes_names}")

        try:
            data = await self.themes.remove_themes(themes_names)
        except IntegrityError as e:
            logger.error(e)
            await event.reply(f"**Ошибка!** Ошибка с удалением вашей темы")
            return

        if data['errors_names']:
            await event.reply(
                f"Были удалены темы, кроме этих\n\n{'-'.join(data['errors_names'])}\n\nТак как их **нет в базе данных**")
        else:
            await event.reply(f"**Были удалены все темы**")

    async def follow_themes_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        command_data = msg.split()
        if len(command_data) != 2:
            await event.reply(f"Вы **ошиблись** в форматом")
            return

        command_data = command_data[1]

        themes_names = list(set([data.replace('+', ' ') for data in command_data.split('-')]))

        logger.info(LoggerTags.COMMAND.value + f" Following {themes_names}")

        try:
            data = await self.themes.follow_themes(themes_names)

        except IntegrityError as e:
            logger.error(e)
            await event.reply("**Ошибка!** Ошибка с обновлением статуса отслеживания темы")
            return

        if data['already_followed']:
            await event.reply(
                f"**Не Обновлен статус отследивания** у тем:\n\n{'-'.join(data['already_followed'])}\n\nТак как они **Уже отслеживаютя**"
            )

        if data['errors_themes']:
            await event.reply(
                f"Обновлен статус отследивания у всех тем, кроме этих\n\n{'-'.join(data['errors_themes'])}\n\nТак как их **нет в базе данных**")
        else:
            await event.reply(f"**Обновлен статус отследивания у всех тем**")

    async def unfollow_themes_command(self, event: events.NewMessage.Event):
        msg = event.message.to_dict()['message']

        command_data = msg.split()
        if len(command_data) != 2:
            await event.reply(f"Вы **ошиблись** в форматом")
            return

        command_data = command_data[1]

        themes_names = list(set(command_data.split('-').replace('+', ' ')))

        logger.info(LoggerTags.COMMAND.value + f" Unfollowing {themes_names}")

        try:
            data = await self.themes.unfollow_themes(themes_names)

        except IntegrityError as e:
            logger.error(e)
            await event.reply("**Ошибка!** Ошибка с обновлением статуса отслеживания темы")
            return

        if data['already_unfollowed']:
            await event.reply(
                f"**Не Обновлен статус отследивания** у тем:\n\n{'-'.join(data['already_unfollowed'])}\n\nТак как они **Не отслеживались ранее**"
            )

        if data['errors_themes']:
            await event.reply(
                f"Обновлен статус отследивания у всех тем, кроме этих\n\n{'-'.join(data['errors_themes'])}\n\nТак как их **нет в базе данных**")
        else:
            await event.reply(f"**Обновлен статус отследивания у всех тем**")

    @check_args_count(2)
    async def change_interval_theme(self, event: events.NewMessage.Event):
        print('called')
        msg = event.message.to_dict()['message']

        msg_words = msg.split()
        payload = msg_words[1].split('-')
        theme_name = payload[0]
        new_interval = payload[1]

        if not new_interval.isdigit():
            await event.reply(
                f"Интервал должен быть **целым числом**"
            )
            return

        try:
            theme = await self.themes.change_interval_theme(theme_name, int(new_interval))
            if theme is None:
                await event.reply(
                    f"**Возникла внутренняя ошибка**\n\nОбратитесь в поддержку"
                )
                return
        except ValueError as e:
            await event.reply(
                f"**Ошибка!**\n\n{e}"
            )
            return

        await event.reply(f"**Успешно обновлено**\n\nНазвание: {theme.theme_name}\nИнтервал: {theme.interval}")


