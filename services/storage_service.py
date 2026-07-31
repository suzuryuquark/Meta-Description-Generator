import flet as ft

from models.generation import DEFAULT_GEMINI_MODEL


class StorageService:
    SETTINGS_SCHEMA_VERSION = 2

    def __init__(self, page: ft.Page):
        self.page = page

    # --- API Key ---
    async def get_api_key(self):
        return await self.page.client_storage.get_async("gemini_api_key")

    async def save_api_key(self, api_key: str):
        await self.page.client_storage.set_async("gemini_api_key", api_key)

    async def has_api_key(self):
        return await self.page.client_storage.contains_key_async("gemini_api_key")

    # --- Gemini Model ---
    async def get_gemini_model(self):
        return await self.page.client_storage.get_async("gemini_model") or DEFAULT_GEMINI_MODEL

    async def save_gemini_model(self, model_name: str):
        await self.page.client_storage.set_async("gemini_model", model_name)

    async def migrate_settings(self):
        current_version = await self.page.client_storage.get_async("settings_schema_version") or 1
        if current_version < 2:
            if not await self.page.client_storage.get_async("gemini_model"):
                await self.save_gemini_model(DEFAULT_GEMINI_MODEL)
            await self.page.client_storage.set_async(
                "settings_schema_version", self.SETTINGS_SCHEMA_VERSION
            )

    # --- Instructions & Keywords ---
    async def get_global_instruction(self):
        return await self.page.client_storage.get_async("global_instruction")

    async def save_global_instruction(self, instruction: str):
        await self.page.client_storage.set_async("global_instruction", instruction)

    async def get_target_keywords(self):
        return await self.page.client_storage.get_async("target_keywords")

    async def save_target_keywords(self, keywords: str):
        await self.page.client_storage.set_async("target_keywords", keywords)

    # --- Templates ---
    async def get_templates(self):
        return await self.page.client_storage.get_async("prompt_templates") or {}

    async def save_templates(self, templates: dict):
        await self.page.client_storage.set_async("prompt_templates", templates)

    # --- History ---
    async def get_history(self):
        return await self.page.client_storage.get_async("generation_history") or []

    async def save_history(self, history: list):
        # Limit to 50 items
        history = history[-50:]
        await self.page.client_storage.set_async("generation_history", history)

    async def clear_history(self):
        await self.page.client_storage.set_async("generation_history", [])

    # --- Session Context ---
    async def get_last_domain(self):
        return await self.page.client_storage.get_async("last_domain")

    async def save_last_domain(self, domain: str):
        await self.page.client_storage.set_async("last_domain", domain)
