import os

import pytest

from services.gemini_service import GeminiService

pytestmark = pytest.mark.live_api


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEYが設定されていないため実APIテストをスキップします",
)
def test_list_live_gemini_models():
    models = GeminiService().list_models(os.environ["GEMINI_API_KEY"])

    assert models
    assert all(model.model_id for model in models)
