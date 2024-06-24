from pprint import pprint
from typing import List, Optional

from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from config import async_session, LoggerTags
from data import (
    ListeningChatModel,
    KeywordsModel,
    ThemeModel,
    MessagesModel,
    FilesModel,
)
from data.interfaces import (
    ListeningChatInterface,
    KeywordInterface,
    MessagesInterface,
    ThemeInterface,
    FilesInterface,
)
from data.dataclasses import ListeningChatsDB, KeywordsDB, MessageDB, FileDB, ThemeDB, AddThemeDB
from data.models import theme_keyword_association

from loguru import logger


class ListeningChatsDataManager(ListeningChatInterface):
    def __init__(self):
        super().__init__()
        self.session = async_session()

    async def all_listening_chats(self) -> List[ListeningChatsDB]:
        logger.debug(f"{LoggerTags.DATABASE.value} All listening chats")
        result = await self.session.execute(select(ListeningChatModel))
        all_chats_models = result.scalars().all()

        all_chats_db = [
            ListeningChatsDB(
                id=chat_model.id,
                chat_id=chat_model.chat_id
            )
            for chat_model in all_chats_models]

        return all_chats_db

    async def add_listening_chat(self, chat_id: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Add listening chat - {chat_id}")
        exists = await self.session.execute(
            select(ListeningChatModel).where(ListeningChatModel.chat_id == chat_id)
        )
        chat = exists.scalars().first()

        if chat is None:
            # Если чата нет, добавляем его
            new_chat = ListeningChatModel(chat_id=chat_id)
            self.session.add(new_chat)
            try:
                await self.session.commit()
            except IntegrityError as e:
                await self.session.rollback()
                raise e

    async def get_listening_chat(self, chat_id: str) -> Optional[ListeningChatsDB]:
        logger.debug(f"{LoggerTags.DATABASE.value} Get listening chat {chat_id}")

        res = await self.session.execute(
            select(ListeningChatModel).where(ListeningChatModel.chat_id == chat_id)
        )
        res = res.scalars().first()

        if not res:
            return None

        return ListeningChatsDB(
            id=res.id,
            chat_id=res.chat_id
        )

    async def remove_listening_chat(self, chat_id: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Remove listening chat {chat_id}")

        await self.session.execute(
            delete(ListeningChatModel).where(ListeningChatModel.chat_id == chat_id)
        )
        await self.session.commit()


class ThemesDataManager(ThemeInterface):
    def __init__(self):
        super().__init__()
        self.session = async_session()

    async def all_themes(self) -> List[ThemeDB]:
        logger.debug(f"{LoggerTags.DATABASE.value} All themes")
        themes_all = await self.session.execute(select(ThemeModel))
        themes_all = themes_all.scalars().all()

        themes = [
            ThemeDB(
                id=theme.id,
                theme_name=theme.theme_name,
                is_following=theme.is_following,
                keywords=await self.get_keyword_list_for_theme(theme.theme_name)
            )
            for theme in themes_all
        ]

        return themes

    async def get_theme(self, theme_name: str) -> Optional[ThemeModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} Get theme {theme_name}")

        theme = await self.session.execute(
            select(ThemeModel).options(joinedload(ThemeModel.keywords)).where(ThemeModel.theme_name == theme_name)
        )
        theme = theme.scalars().first()

        return theme

    async def get_keyword_list_for_theme(self, theme_name: str) -> List[KeywordsDB]:
        logger.debug(f"{LoggerTags.DATABASE.value} Get keywords for theme {theme_name}")

        theme = await self.session.execute(
            select(ThemeModel).options(joinedload(ThemeModel.keywords)).where(ThemeModel.theme_name == theme_name)
        )
        theme = theme.scalars().first()
        if theme:
            return [
                KeywordsDB(
                    id=keyword.id,
                    word=keyword.word
                ) for keyword in theme.keywords]
        return []

    async def add_keyword_to_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        logger.debug(LoggerTags.DATABASE.value[0] + f" Adding {keywords} keywords to {theme_name}")

        old_keywords = await self.get_keyword_list_for_theme(theme_name)
        old_keywords_words = [el.word for el in old_keywords]

        theme_db = await self.get_theme(theme_name)

        if theme_db is None:
            raise KeyError(f"Нет такой темы '{theme_name}'")

        for keyword in keywords:
            if keyword.word not in old_keywords_words:

                kw = await self.session.execute(
                    select(KeywordsModel).where(KeywordsModel.word == keyword.word)
                )
                kw = kw.scalars().first()

                theme_db.keywords.append(kw)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def remove_keywords_from_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        logger.debug(f"{LoggerTags.DATABASE.value} Removing keywords from {theme_name}")

        theme_db = await self.get_theme(theme_name)

        if theme_db is None:
            raise KeyError(f"Нет такой темы '{theme_name}'")

        for keyword in keywords:
            keyword_db = await self.session.execute(
                select(KeywordsModel).where(KeywordsModel.word == keyword.word)
            )
            keyword_db = keyword_db.scalars().first()

            if keyword_db and keyword_db in theme_db.keywords:
                theme_db.keywords.remove(keyword_db)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def add_theme(self, theme: AddThemeDB):
        logger.debug(f"{LoggerTags.DATABASE.value} Add theme {theme.theme_name}")

        keywords = []

        for keyword_name in theme.keywords:
            exists = await self.session.execute(
                select(KeywordsModel).where(KeywordsModel.word == keyword_name.word)
            )
            keyword = exists.scalars().first()
            if keyword is None:
                keyword = KeywordsModel(word=keyword_name)
                self.session.add(keyword)
                await self.session.commit()
            keywords.append(keyword)

        new_theme = ThemeModel(theme_name=theme.theme_name, keywords=keywords)
        self.session.add(new_theme)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def remove_themes(self, themes: List[ThemeModel]):
        logger.debug(f"{LoggerTags.DATABASE.value} Remove themes")
        for theme in themes:
            await self.remove_theme(theme.theme_name)

    async def remove_theme(self, theme_name: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Removing theme with {theme_name=}")

        theme_db = await self.get_theme(theme_name)

        if theme_db is None:
            raise KeyError(f"Нет такой темы '{theme_name}'")

        keywords = theme_db.keywords

        await self.session.execute(
            delete(ThemeModel).where(ThemeModel.theme_name == theme_name)
        )

        for keyword in keywords:
            await self.session.execute(
                delete(theme_keyword_association).where(
                    (theme_keyword_association.c.theme_id == theme_db.id) &
                    (theme_keyword_association.c.keyword_id == keyword.id)
                )
            )

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def follow_theme(self, theme_name: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Following theme with {theme_name=}")

        theme_db = await self.get_theme(theme_name)

        if theme_db is None:
            raise KeyError(f"Нет такой темы '{theme_name}'")

        theme_db.is_following = True

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def unfollow_theme(self, theme_name: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Unfollowing theme with {theme_name=}")

        theme_db = await self.get_theme(theme_name)

        if theme_db is None:
            raise KeyError(f"Нет такой темы '{theme_name}'")

        theme_db.is_following = False

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def follow_themes(self, theme_names: List[str]):
        logger.debug(f"{LoggerTags.DATABASE.value} Following themes with {theme_names=}")

        _ = [await self.follow_theme(name) for name in theme_names]

    async def unfollow_themes(self, theme_names: List[str]):
        logger.debug(f"{LoggerTags.DATABASE.value} Following themes with {theme_names=}")

        _ = [await self.unfollow_theme(name) for name in theme_names]


class KeywordsDataManager(KeywordInterface):
    def __init__(self):
        super().__init__()
        self.session = async_session()

    async def all_keywords(self) -> List[KeywordsDB]:
        logger.debug(f"{LoggerTags.DATABASE.value} Getting all keywords")
        res = await self.session.execute(select(KeywordsModel))
        res = res.scalars().all()

        all_models = [
            KeywordsDB(
                id=keyword_model.id,
                word=keyword_model.word
            )
            for keyword_model in res
        ]

        return all_models

    async def add_keyword(self, keyword_name: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Adding keyword {keyword_name=}")
        exists = await self.session.execute(
            select(KeywordsModel).where(KeywordsModel.word == keyword_name)
        )
        kn = exists.scalars().first()

        if kn is None:
            self.session.add(KeywordsModel(word=keyword_name))
            try:
                await self.session.commit()
            except IntegrityError as e:
                await self.session.rollback()
                raise e

    async def get_keyword(self, keyword_name: str) -> Optional[KeywordsDB]:
        logger.debug(f"{LoggerTags.DATABASE.value} Getting keyword {keyword_name=}")
        exists = await self.session.execute(
            select(KeywordsModel).where(KeywordsModel.word == keyword_name)
        )
        kn = exists.scalars().first()

        if kn is not None:
            return KeywordsDB(
                id=kn.id,
                word=kn.word
            )
        return None

    async def add_keywords(self, keyword_names: list[str]):
        logger.debug(f"{LoggerTags.DATABASE.value} Adding keywords {keyword_names=}")
        _ = [await self.add_keyword(keyword_name) for keyword_name in keyword_names]

    async def remove_keyword(self, keyword_name: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Removing keyword {keyword_name=}")
        await self.session.execute(
            delete(KeywordsModel).where(KeywordsModel.word == keyword_name)
        )
        await self.session.commit()

    async def remove_keywords(self, keyword_names: list[str]):
        logger.debug(f"{LoggerTags.DATABASE.value} Removing keywords {keyword_names=}")
        _ = [await self.remove_keyword(keyword_name) for keyword_name in keyword_names]

    async def edit_keyword(self, from_kw: str, to_kw) -> Optional[KeywordsModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} Editing keyword {from_kw} to {to_kw}")
        to_kw_exists = await self.session.execute(
            select(KeywordsModel).where(KeywordsModel.word == to_kw)
        )
        kn = to_kw_exists.scalars().first()

        if kn is not None:
            raise ValueError(f"Слово '{to_kw}' уже существует.")

        # Обновляем ключевое слово
        result = await self.session.execute(
            update(KeywordsModel)
            .where(KeywordsModel.word == from_kw)
            .values(word=to_kw)
            .returning(KeywordsModel)
        )
        updated_keyword = result.scalars().first()

        if updated_keyword is not None:
            try:
                await self.session.commit()
                return updated_keyword
            except IntegrityError as e:
                await self.session.rollback()
                raise e

        return None


class MessagesDataManager(MessagesInterface):
    def __init__(self):
        super().__init__()
        self.asession = async_session

    async def all_messages(self) -> List[MessagesModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} All messages")
        async with self.asession() as session:
            res = await session.execute(select(MessagesModel))
            return res.scalars().all()

    async def get_message(self, message_id: str, chat_id: str) -> Optional[MessagesModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} Get message {message_id} from chat {chat_id}")
        async with self.asession() as session:
            res = await session.execute(
                select(MessagesModel).where(
                    MessagesModel.message_id == message_id,
                    MessagesModel.chat_id == chat_id
                )
            )
            return res.scalars().first()

    async def add_message(self, message: MessageDB):
        logger.debug(f"{LoggerTags.DATABASE.value} Add message")
        async with self.asession() as session:
            exists = await self.get_message(message.message_id, message.chat_id)

            if exists is None:
                msg = MessagesModel(
                    chat_id=message.chat_id,
                    message_id=message.message_id,
                    message=message.message,
                    grouped_id=message.grouped_id,
                    date=message.date,
                    links=message.links
                )
                session.add(msg)

            try:
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                raise e

    async def remove_message(self, message_id: str, chat_id: str):
        logger.debug(f"{LoggerTags.DATABASE.value} Remove message {message_id} from chat {chat_id}")

        async with self.asession() as session:
            await session.execute(
                delete(MessagesModel).where(
                    MessagesModel.message_id == message_id,
                    MessagesModel.chat_id == chat_id
                )
            )
            await session.commit()


class FilesDataManager(FilesInterface):
    def __init__(self):
        super().__init__()
        self.asession = async_session

    async def all_files(self) -> List[FilesModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} All files")
        async with self.asession() as session:
            res = await session.execute(select(FilesModel))
            return res.scalars().all()

    async def add_file(self, file: FileDB):
        logger.debug(f"{LoggerTags.DATABASE.value} Adding file")

        async with self.asession() as session:

            exists = await self.get_file(file.document_id)

            if exists is None:
                session.add(
                    FilesModel(
                        document_id=file.document_id,
                        file_name=file.file_name,
                        file_type=file.file_type,
                        file_path=file.file_path,
                        message_id=file.message_id,
                        chat_id=file.chat_id,
                        original_filename=file.original_filename
                    )
                )
                try:
                    await session.commit()
                except IntegrityError as e:
                    await session.rollback()
                    raise e

    async def get_file(self, document_id: str) -> Optional[FilesModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} Get file {document_id=}")

        async with self.asession() as session:
            res = await session.execute(
                select(FilesModel).where(FilesModel.document_id == document_id)
            )

            return res.scalars().first()

    async def get_files_for_message(self, chat_id: str, message_id: str) -> List[FilesModel]:
        logger.debug(f"{LoggerTags.DATABASE.value} Get file {message_id=} {chat_id=}")

        async with self.asession() as session:

            res = await session.execute(
                select(FilesModel).where(
                    FilesModel.message_id == message_id,
                    FilesModel.chat_id == chat_id
                )
            )

            return res.scalars().all()

    async def remove_file(self,
                          document_id: Optional[str] = None,
                          message_id: Optional[str] = None,
                          chat_id: Optional[str] = None):
        """
        Remove file from database. File in directory will not be removed.

        You can use only document_id or message_id with chat_id both

        :param document_id:
        :param message_id:
        :param chat_id:
        :return:
        """

        logger.debug(f"{LoggerTags.DATABASE.value} Remove file {document_id=} {message_id=} {chat_id=}")

        async with self.asession() as session:
            if document_id:
                await session.execute(
                    delete(FilesModel).where(FilesModel.document_id == document_id)
                )
            elif message_id and chat_id:
                await session.execute(
                    delete(FilesModel).where(
                        FilesModel.message_id == message_id,
                        FilesModel.chat_id == chat_id
                    )
                )

            await session.commit()


class DBManager:
    def __init__(self):
        # self.all_chats = AllChatsDataManager()
        self.listening_chats = ListeningChatsDataManager()
        self.messages = MessagesDataManager()
        self.keywords = KeywordsDataManager()
        self.themes = ThemesDataManager()
        self.files = FilesDataManager()
