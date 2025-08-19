import pytest

from llm_browser.main import main


@pytest.mark.parametrize("urls_limit,roles_limit", [(2, 2)])
def test_main(urls_limit, roles_limit):
    try:
        main(urls_limit=urls_limit, roles_limit=roles_limit)
    except Exception as e:
        pytest.fail(f"main function raised an exception: {e}")
