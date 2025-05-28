import logging

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from llm_browser.src.configs.config import results_dir
from llm_browser.src.utils import set_logging

set_logging()
logger = logging.getLogger(__name__)


def extract_transcript(url: str):
    """Extracts the Fireflies transcript

    Args
    ---
    url: of the Fireflies transcript
    """

    meeting_name = url.split("::")[0].split("/")[-1]
    file_name = f"{meeting_name}.txt"
    file_path = results_dir / file_name

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector(".paragraph-root")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("div", class_="paragraph-root")

    markdown_output = []

    for para in paragraphs:
        # Extract name
        name_span = para.find("span", class_="name")
        name = name_span.text.strip() if name_span else "Unknown"

        # Extract timestamp
        timestamp_span = para.find("span", class_="sc-871c1b8d-0")
        timestamp = timestamp_span.text.strip() if timestamp_span else "00:00"

        # Extract message
        message_div = para.find("div", class_="transcript-sentence")
        message = message_div.text.strip() if message_div else ""

        # Format the line
        markdown_line = f"{name} - {timestamp}\n{message}\n\n"

        markdown_output.append(markdown_line)

    with open(file_path, "w") as f:
        f.writelines(markdown_output)

    logger.info(f"transcript saved to {file_path.resolve()}")


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Extracts the Fireflies transcript")
    parser.add_argument("--url", help="url to the transcript", type=str)
    args = parser.parse_args()

    extract_transcript(url=args.url)
