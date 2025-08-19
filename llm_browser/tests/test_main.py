import pytest

from llm_browser.main import main


def test_main(urls_limit=2, roles_limit=2):
    try:
        main(urls_limit=urls_limit, roles_limit=roles_limit)
    except Exception as e:
        pytest.fail(f"main function raised an exception: {e}")
    assert True, "main function executed successfully"
