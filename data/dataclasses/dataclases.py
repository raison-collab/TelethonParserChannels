import datetime
from abc import ABCMeta
from dataclasses import dataclass
from typing import Dict, List, Optional


class BaseChat(metaclass=ABCMeta):
    def to_dict(self) -> Dict[str, str]:
        pass


@dataclass
class ChatIdMixin:
    chat_id: str


@dataclass
class ChatNameMixin:
    chat_name: str


@dataclass
class AddChatDB(ChatIdMixin, ChatNameMixin, BaseChat):
    def to_dict(self) -> Dict[str, str]:
        return {
            'chat_id': self.chat_id,
            'chat_name': self.chat_name
        }


@dataclass
class AllChatsDB(ChatIdMixin, ChatNameMixin, BaseChat):
    id: int

    def to_dict(self) -> Dict[str, str]:
        return {
            'chat_id': self.chat_id,
            'chat_name': self.chat_name
        }


@dataclass
class ListeningChatsDB(ChatIdMixin, BaseChat):
    id: int

    def to_dict(self) -> Dict[str, str]:
        return {
            'chat_id': self.chat_id
        }


async def compare_chats_by_chat_id(chat1: ChatIdMixin, chat2: ChatIdMixin) -> bool:
    return str(chat1.chat_id) == str(chat2.chat_id)


@dataclass
class KeywordsDB:
    id: int
    word: str


async def compare_keywords_by_word(kw1: KeywordsDB, kw2: KeywordsDB) -> bool:
    return str(kw1.word) == str(kw2.word)


@dataclass
class ThemeDB:
    id: int
    theme_name: str
    is_following: bool
    interval: int
    keywords: List[KeywordsDB]


@dataclass
class AddThemeDB:
    theme_name: str
    interval: int
    keywords: List[KeywordsDB]


@dataclass
class FileDB(ChatIdMixin):
    document_id: str
    file_name: str
    file_path: str
    file_type: str
    message_id: str
    original_filename: Optional[str] = None


@dataclass
class MessageDB(ChatIdMixin):
    message_id: str
    message: str
    date: datetime.datetime
    links: Optional[str] = None
    grouped_id: Optional[int] = None
