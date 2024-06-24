from abc import ABCMeta
from typing import List, Optional

from . import KeywordsModel, ThemeModel, MessagesModel
from .dataclasses import ListeningChatsDB, KeywordsDB, MessageDB, ThemeDB, AddThemeDB, FileDB
from .models import FilesModel


class ListeningChatInterface(metaclass=ABCMeta):
    async def all_listening_chats(self) -> List[ListeningChatsDB]:
        pass

    async def add_listening_chat(self, chat_id: str):
        pass

    async def get_listening_chat(self, chat_id: str) -> Optional[ListeningChatsDB]:
        pass

    async def remove_listening_chat(self, chat_id: str):
        pass


class KeywordInterface(metaclass=ABCMeta):
    async def all_keywords(self) -> List[KeywordsDB]:
        pass

    async def add_keyword(self, keyword_name: str):
        pass

    async def add_keywords(self, keyword_names: str):
        pass

    async def get_keyword(self, keyword_name: str) -> Optional[KeywordsDB]:
        pass

    async def remove_keyword(self, keyword_name: str):
        pass

    async def remove_keywords(self, keyword_names: list[str]):
        pass

    async def edit_keyword(self, from_kw: str, to_kw) -> Optional[KeywordsModel]:
        pass


class ThemeInterface(metaclass=ABCMeta):
    async def all_themes(self) -> List[ThemeDB]:
        pass

    async def get_theme(self, theme_name: str) -> Optional[ThemeModel]:
        pass

    async def get_keyword_list_for_theme(self, theme_name: str) -> List[KeywordsDB]:
        pass

    async def add_keyword_to_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        pass

    async def remove_keywords_from_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        pass

    async def add_theme(self, theme: AddThemeDB):
        pass

    async def add_themes(self, themes: List[AddThemeDB]):
        pass

    async def follow_theme(self, theme_name: str):
        pass

    async def unfollow_theme(self, theme_name: str):
        pass

    async def follow_themes(self, theme_names: List[str]):
        pass

    async def unfollow_themes(self, theme_names: List[str]):
        pass

    async def remove_theme(self, theme_name: str):
        pass

    async def remove_themes(self, theme_names: List[str]):
        pass


class MessagesInterface(metaclass=ABCMeta):
    async def all_messages(self) -> List[MessagesModel]:
        pass

    async def get_message(self, message_id: str, chat_id: str) -> Optional[MessagesModel]:
        pass

    async def add_message(self, message: MessageDB):
        pass

    async def remove_message(self, message_id: str, chat_id: str):
        pass


class FilesInterface(metaclass=ABCMeta):
    async def all_files(self) -> List[FilesModel]:
        pass

    async def get_file(
            self,
            document_id: str
    ) -> Optional[FilesModel]:
        pass

    async def get_files_for_message(self,chat_id: str, message_id: str) -> List[FilesModel]:
        pass

    async def add_file(self, file: FileDB):
        pass

    async def remove_file(
            self,
            document_id: Optional[str] = None,
            message_id: Optional[str] = None,
            chat_id: Optional[str] = None
    ):
        pass
