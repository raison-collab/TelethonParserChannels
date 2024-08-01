import asyncio
import os
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List

from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from telethon.tl.types import InputMediaPhoto, InputMediaDocument, MessageMediaPhoto, MessageMediaDocument, \
    TypeDocumentAttribute, DocumentAttributeFilename

from config import scheduler, TIMEZONE, client, MessageFiletypes, LoggerTags, BOT_URL
from data import MessagesModel
from data.db_manager import DBManager


class SchedulerManager(metaclass=ABCMeta):
    def __init__(self):
        self.scheduler = scheduler
        self.client = client
        self.db_manager = DBManager()

    @abstractmethod
    async def _send_messages(self, messages: List[MessagesModel]):
        logger.info(f"{LoggerTags.SCHEDULER.value} Sending {len(messages)} messages")
        pass


class ThemeSchedulerManager(SchedulerManager):
    def __init__(self):
        super().__init__()

    async def _get_messages_by_interval(self, interval: int) -> Optional[List[MessagesModel]]:
        logger.debug(f"{LoggerTags.SCHEDULER.value} Getting messages by {interval=}")
        utc_now = datetime.now(TIMEZONE)

        start_time = utc_now - timedelta(seconds=interval + 15)

        return await self.db_manager.messages.get_message_by_interval(start_time)

    async def _send_messages(self, messages: List[MessagesModel]):
        logger.info(f"{LoggerTags.SCHEDULER.value} Sending {len(messages)} messages")

        is_file_sent = False

        for message in messages:
            grouped_msgs = []

            if message.grouped_id:
                grouped_msgs = [
                    msg for msg in messages
                    if msg.grouped_id == message.grouped_id and
                       msg.chat_id == message.chat_id
                ]
            else:
                grouped_msgs.append(message)

            media = []

            for msg in grouped_msgs:
                media += await self.db_manager.files.get_files_for_message(msg.chat_id, msg.message_id)

            if media and not is_file_sent:
                logger.debug(f"Sending media files for message {message.message_id} from chat {message.chat_id}")
                await self.client.send_file(
                    entity=BOT_URL,
                    file=[el.file_path for el in media],
                    caption=message.message if message.message else "",
                )
                is_file_sent = True

            else:
                logger.debug(f"Sending text message {message.message_id} in chat {message.chat_id}")
                await self.client.send_message(
                    entity=BOT_URL,
                    message=message.message
                )
            await asyncio.sleep(0.3)

    async def _send_messages_job(self, interval: int):
        logger.info(f"{LoggerTags.SCHEDULER.value} - Sending messages job")
        try:
            msgs = await self._get_messages_by_interval(interval)
            await self._send_messages(msgs)
        except Exception as e:
            logger.error(f"Error sending messages: {e}")

    async def add_new_theme_job(self, theme_name: str, interval: int):
        logger.info(f"{LoggerTags.SCHEDULER.value} Adding new schedule for theme {theme_name=}")
        self.scheduler.add_job(self._send_messages_job, IntervalTrigger(seconds=interval), args=[interval],
                               id=theme_name)

    async def remove_theme_job(self, theme_name: str):
        logger.info(f"{LoggerTags.SCHEDULER.value} Removing schedule for theme {theme_name=}")
        self.scheduler.remove_job(theme_name)

    async def update_theme_job_interval(self, theme_name: str, new_interval: int):
        logger.info(
            f"{LoggerTags.SCHEDULER.value} Updating schedule for theme {theme_name=} with new interval {new_interval=}")
        await self.remove_theme_job(theme_name)
        await self.add_new_theme_job(theme_name, new_interval)
