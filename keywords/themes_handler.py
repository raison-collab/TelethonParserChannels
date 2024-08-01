from typing import List, Optional

from loguru import logger

from config import async_session, LoggerTags
from data import ThemeModel
from data.dataclasses import AddThemeDB, KeywordsDB
from data.db_manager import DBManager
from scheduler_manager import ThemeSchedulerManager


class ThemesHandler:
    def __init__(self):
        self.session = async_session()
        self.db_manager = DBManager()
        self.scheduler = ThemeSchedulerManager()

    async def all_themes(self):
        logger.info(f"{LoggerTags.HANDLER.value} Getting all themes")
        return await self.db_manager.themes.all_themes()

    async def add_theme(self, theme_name: str, interval: int, keywords: List[KeywordsDB]):
        logger.info(LoggerTags.HANDLER.value + f" Adding theme with {theme_name=}")
        await self.db_manager.themes.add_theme(
            AddThemeDB(
                theme_name=theme_name,
                interval=interval,
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
        already_followed = []

        for theme_name in theme_names:
            if theme_name not in old_themes_names:
                errors_themes.append(theme_name)
                continue

            th = await self.db_manager.themes.get_theme(theme_name)
            if th.is_following:
                already_followed.append(theme_name)
                continue

            valid_themes.append(theme_name)

        await self.db_manager.themes.follow_themes(valid_themes)

        for theme_name_ in valid_themes:
            await self.scheduler.add_new_theme_job(theme_name_, [el.interval for el in old_themes if el.theme_name == theme_name_][0])

        return {
            'valid_themes': valid_themes,
            'errors_themes': errors_themes,
            'already_followed': already_followed
        }

    async def unfollow_themes(self, theme_names: List[str]) -> dict[str, List[str]]:
        logger.info(f"{LoggerTags.HANDLER.value} Unfollowing themes {theme_names}")

        old_themes = await self.db_manager.themes.all_themes()
        old_themes_names = [theme.theme_name for theme in old_themes]

        errors_themes = []
        valid_themes = []
        already_unfollowed = []

        for theme_name in theme_names:
            if theme_name not in old_themes_names:
                errors_themes.append(theme_name)
                continue

            th = await self.db_manager.themes.get_theme(theme_name)
            if not th.is_following:
                already_unfollowed.append(theme_name)
                continue

            valid_themes.append(theme_name)

        await self.db_manager.themes.unfollow_themes(valid_themes)

        for theme_name_ in valid_themes:
            await self.scheduler.remove_theme_job(theme_name_)

        return {
            'valid_themes': valid_themes,
            'errors_themes': errors_themes,
            'already_unfollowed': already_unfollowed
        }

    async def change_interval_theme(self, theme_name: str, new_interval_seconds: int) -> Optional[ThemeModel]:
        logger.info(f"{LoggerTags.HANDLER.value} Change interval for {theme_name=} on {new_interval_seconds=}")

        all_themes_names = [el.theme_name for el in await self.all_themes()]

        if theme_name not in all_themes_names:
            raise ValueError(f"Такой темы нет")

        updated_theme = await self.db_manager.themes.change_interval(theme_name, new_interval_seconds)
        await self.scheduler.update_theme_job_interval(theme_name, new_interval_seconds)

        return updated_theme
