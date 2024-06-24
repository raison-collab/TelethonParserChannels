import datetime
import os
import re
from pprint import pprint

import pytz
from loguru import logger
from sqlalchemy.exc import IntegrityError
from telethon import events, TelegramClient, types
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

from config import LISTENING_CHATS_FILENAME, ALL_CHATS_FILENAME, BOT_URL, LoggerTags, UPLOAD_FOLDER, MessageFiletypes
from data import FilesModel
from data.dataclasses import AddChatDB, MessageDB, FileDB
from data.db_manager import DBManager
from keywords import KeywordsHandler


class ChatsHandler:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.kh = KeywordsHandler()
        self.db_manager = DBManager()

    async def check_chat_existing(self, chat: str | int) -> bool:
        """
        проверить наличие чата среди всех чатов пользователя
        проверка только на чаты, где chat_id - число, а не ссылка
        :param chat:
        :return:
        """
        return True if chat in [str(el.entity.id) for el in await self.client.get_dialogs()] else False

    async def check_chat_existing_in_db(self, chat: str) -> bool:
        """
        Проверить наличие чата среди прослушиваемых
        :param chat:
        :return:
        """
        return True if await self.db_manager.listening_chats.get_listening_chat(chat) is not None else False

    async def listening_chats_list(self) -> list:
        """
        Получить список прослушиваемых чатов
        :return:
        """
        res = await self.db_manager.listening_chats.all_listening_chats()
        return [int(el.chat_id) if el.chat_id.isdigit() else el.chat_id for el in res]

    async def create_all_chats_file(self, path: str, data: str):
        """
        Создает файл со всеми чатами и их ID
        :param path: путь к файлу
        :param data: данные в виде строки
        """
        with open(path, 'w', encoding='utf8') as f:
            f.write(data)

    async def normal_handler(self, event: events.NewMessage.Event):
        """
        Обработчик чатов, у которых срабатывает событие на новые сообщения
        """
        logger.info(f"{LoggerTags.HANDLER.value} Detected new message from {event.message.peer_id.channel_id}")

        moscow_tz = pytz.timezone('Europe/Moscow')
        new_date = event.message.date.astimezone(moscow_tz)

        link_pattern = re.compile(r'/\[([^/\]]+)/\]\((https?://[^/\)]+)/\)')

        links_ent = event.message.entities

        links = []

        if links_ent:
            links = [link.url for link in links_ent if isinstance(link, types.MessageEntityTextUrl)]

        message_data = MessageDB(
            chat_id=str(event.chat.id),
            message_id=str(event.message.id),
            message=event.message.message,
            grouped_id=event.message.grouped_id,
            date=new_date,
            links=','.join(links) if links else None
        )

        await self.db_manager.messages.add_message(message_data)

        if event.message.media:

            if isinstance(event.message.media, types.MessageMediaWebPage):
                logger.info(f'{LoggerTags.HANDLER.value} Detected web page')
                return

            logger.info(f'{LoggerTags.HANDLER.value} Detected media')
            file_name = file_type = document_id = original_filename = None

            if isinstance(event.message.media, MessageMediaPhoto):
                file_name = f"{event.message.photo.id}-{event.chat.id}-{event.message.id}{event.message.file.ext}"
                file_type = MessageFiletypes.DOCUMENT.value
                document_id = event.message.photo.id

            elif isinstance(event.message.media, MessageMediaDocument):
                file_name = f"{event.message.document.id}-{event.chat.id}-{event.message.id}{event.message.file.ext}"
                file_type = MessageFiletypes.DOCUMENT.value
                document_id = event.message.document.id

            if hasattr(event.message.media, 'document'):
                document = event.message.media.document

                for attribute in document.attributes:
                    if isinstance(attribute, types.DocumentAttributeFilename):
                        original_filename = attribute.file_name.split('.')[0]

            file_path = f"{UPLOAD_FOLDER}/{file_type}/{file_name}"
            await self.client.download_media(event.message.media, file_path)

            file_record = FileDB(
                document_id=document_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                message_id=event.message.id,
                chat_id=event.chat.id,
                original_filename=original_filename
            )

            # todo при отправке нескольких фото, прикрепленных к сообщению, сохраняются не все
            await self.db_manager.files.add_file(file_record)

        if await self.kh.check_contains(event.message.text.lower().replace("ё", "е")):
            logger.info(f"{LoggerTags.HANDLER.value} Forward message id={message_data.message_id} from {message_data.chat_id} to moderation chat")
            await self.client.forward_messages(BOT_URL, event.message)

    async def add_chat(self, chat: str | int):
        """
        Добавить чат для прослушиваняи
        :param chat: ссылка на чат или id
        """

        if await self.check_chat_existing_in_db(str(chat)):
            raise KeyError("Чат уже был добавлен")

        try:
            await self.db_manager.listening_chats.add_listening_chat(str(chat))
        except IntegrityError:
            raise ValueError("Возможно вы передали идентификатор чата, который уже прослушиваете")

        # self.client.add_event_handler(self.normal_handler, events.NewMessage(chats=await self.listening_chats_list()))
        logger.info(f'{LoggerTags.HANDLER.value} Added chat - {chat}')

    async def remove_chat(self, chat: str | int):
        """
        Удаление чата из списка прослушиваемых
        :param chat:
        :return:
        """

        if not await self.check_chat_existing_in_db(str(chat)):
            raise KeyError("Такого чата нет среди добавленных для прослушивания")

        await self.db_manager.listening_chats.remove_listening_chat(chat)

        self.client.add_event_handler(self.normal_handler, events.NewMessage(chats=await self.listening_chats_list()))
        logger.info(f'{LoggerTags.HANDLER.value} Removed chat - {chat}')
