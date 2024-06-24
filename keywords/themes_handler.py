from typing import List

from loguru import logger

from config import async_session, LoggerTags
from data.dataclasses import AddThemeDB, KeywordsDB
from data.db_manager import DBManager


class ThemesHandler:
    def __init__(self):
        self.session = async_session()
        self.db_manager = DBManager()

    async def all_themes(self):
        logger.info(f"{LoggerTags.HANDLER.value} Getting all themes")
        return await self.db_manager.themes.all_themes()

    async def add_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        logger.info(LoggerTags.HANDLER.value + f" Adding theme with {theme_name=}")
        await self.db_manager.themes.add_theme(
            AddThemeDB(
                theme_name=theme_name,
                keywords=keywords
            )
        )

    async def add_keyword_to_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        logger.info(LoggerTags.HANDLER.value + f" Adding keyword to theme with {theme_name=}")

        await self.db_manager.themes.add_keyword_to_theme_command(theme_name, keywords)

    async def remove_keywords_from_theme(self, theme_name: str, keywords: List[KeywordsDB]):
        logger.info(f"{LoggerTags.HANDLER.value} Removing keyword from theme with {theme_name=}")

        await self.db_manager.themes.remove_keywords_from_theme(theme_name, keywords)

    async def remove_themes(self, theme_names: List[str]) -> dict[str, List[str]]:
        logger.info(f"{LoggerTags.HANDLER.value} Removing themes from")

        old_themes = await self.db_manager.themes.all_themes()
        old_themes_names = [el.theme_name for el in old_themes]

        errors_names = []
        valid_names = []

        for theme_name in theme_names:
            if theme_name not in old_themes_names:
                errors_names.append(theme_name)
                continue
            valid_names.append(theme_name)

        theme_models = [
            await self.db_manager.themes.get_theme(name)
            for name in valid_names]

        await self.db_manager.themes.remove_themes(theme_models)

        return {
            'valid_names': valid_names,
            'errors_names': errors_names
        }

    async def follow_themes(self, theme_names: List[str]) -> dict[str, List[str]]:
        logger.info(f"{LoggerTags.HANDLER.value} Following themes {theme_names}")

        old_themes = await self.db_manager.themes.all_themes()
        old_themes_names = [theme.theme_name for theme in old_themes]

        errors_themes = []
        valid_themes = []

        for theme_name in theme_names:
            if theme_name not in old_themes_names:
                errors_themes.append(theme_name)
                continue
            valid_themes.append(theme_name)

        await self.db_manager.themes.follow_themes(valid_themes)

        return {
            'valid_themes': valid_themes,
            'errors_themes': errors_themes
        }

    async def unfollow_themes(self, theme_names: List[str]) -> dict[str, List[str]]:
        logger.info(f"{LoggerTags.HANDLER.value} Following themes {theme_names}")

        old_themes = await self.db_manager.themes.all_themes()
        old_themes_names = [theme.theme_name for theme in old_themes]

        errors_themes = []
        valid_themes = []

        for theme_name in theme_names:
            if theme_name not in old_themes_names:
                errors_themes.append(theme_name)
                continue
            valid_themes.append(theme_name)

        await self.db_manager.themes.unfollow_themes(valid_themes)

        return {
            'valid_themes': valid_themes,
            'errors_themes': errors_themes
        }

