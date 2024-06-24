from typing import Optional

import pymorphy2
from loguru import logger

from config import KEYWORDS_FILENAME, LoggerTags, IGNORE_SYMBOLS
from data.dataclasses import KeywordsDB
from data.db_manager import DBManager


class KeywordsHandler:
    def __init__(self):
        self.pymorphy2_311_hotfix()
        self.morph = pymorphy2.MorphAnalyzer()
        self.db_manager = DBManager()

    def pymorphy2_311_hotfix(self):
        from inspect import getfullargspec
        from pymorphy2.units.base import BaseAnalyzerUnit

        def _get_param_names_311(klass):
            if klass.__init__ is object.__init__:
                return []
            args = getfullargspec(klass.__init__).args
            return sorted(args[1:])

        setattr(BaseAnalyzerUnit, '_get_param_names', _get_param_names_311)

    async def add_keyword(self, keyword: str) -> list:
        word_variants = self.morph.parse(keyword)

        keywords = set()

        for word in word_variants:
            lex = [el.word for el in word.lexeme]

            for variant in lex:
                keywords.add(variant.replace("ё", "е"))

        await self.db_manager.keywords.add_keywords(list(keywords))

        logger.info(f"{LoggerTags.HANDLER.value} Added keywords from word '{keyword}'")
        return list(keywords)

    async def get_keywords(self) -> set:
        logger.info(f"{LoggerTags.HANDLER.value} Getting keywords from database")
        return set([el.word for el in await self.db_manager.keywords.all_keywords()])

    async def get_keyword(self, word: str) -> Optional[KeywordsDB]:
        logger.info(f"{LoggerTags.HANDLER.value} Getting keyword {word}")
        return await self.db_manager.keywords.get_keyword(word)

    async def remove_keyword(self, keyword: str):
        if keyword in [el.word for el in await self.db_manager.keywords.all_keywords()]:
            await self.db_manager.keywords.remove_keyword(keyword)
            logger.info(f"{LoggerTags.HANDLER.value} Removed Keyword from words '{keyword}'")
            return
        raise KeyError(f"Данное ключевое слово - '{keyword}' отсутвует в базе данных")

    async def check_contains(self, msg: str) -> bool:
        logger.info(f"{LoggerTags.HANDLER.value} Checking if message contains '{msg}'")
        message = msg

        for symbol in list(IGNORE_SYMBOLS):
            message = message.replace(symbol, '')

        logger.debug(f"Refactored message: {message}")

        sp = set(message.split())
        kws = await self.get_keywords()
        sp_bool = bool(await self.get_keywords() & set(message.split()))

        return bool(await self.get_keywords() & set(message.split()))

    async def remove_keywords(self, keywords: list[str]):
        await self.db_manager.keywords.remove_keywords(keywords)
        logger.info(f"{LoggerTags.HANDLER.value} Removed keywords {keywords} from database")

    async def edit_keyword(self, from_kw: str, to_kw: str):
        logger.info(f"{LoggerTags.HANDLER.value} Editing keyword from '{from_kw}' to '{to_kw}'")

        exists = await self.db_manager.keywords.get_keyword(from_kw)
        if exists is None:
            raise ValueError(f"Слово, которое вы хотите изменить не записано в базу данных")

        await self.db_manager.keywords.edit_keyword(from_kw, to_kw)


