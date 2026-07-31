import asyncio

from models.generation import DEFAULT_GEMINI_MODEL
from services.storage_service import StorageService


class FakeClientStorage:
    def __init__(self, values=None):
        self.values = values or {}

    async def get_async(self, key):
        return self.values.get(key)

    async def set_async(self, key, value):
        self.values[key] = value

    async def contains_key_async(self, key):
        return key in self.values


class FakePage:
    def __init__(self, values=None):
        self.client_storage = FakeClientStorage(values)


def test_migrate_settings_adds_default_model_without_losing_data():
    page = FakePage({"generation_history": [{"url": "https://example.com"}]})
    storage = StorageService(page)

    asyncio.run(storage.migrate_settings())

    assert page.client_storage.values["gemini_model"] == DEFAULT_GEMINI_MODEL
    assert page.client_storage.values["settings_schema_version"] == 2
    assert page.client_storage.values["generation_history"] == [{"url": "https://example.com"}]


def test_migrate_settings_preserves_selected_model():
    page = FakePage(
        {
            "gemini_model": "gemini-custom",
            "settings_schema_version": 1,
        }
    )
    storage = StorageService(page)

    asyncio.run(storage.migrate_settings())

    assert asyncio.run(storage.get_gemini_model()) == "gemini-custom"
    assert page.client_storage.values["settings_schema_version"] == 2
