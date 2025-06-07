# LLM Browser
## About
The LLM Browser is a Python project that uses Large Language Models (LLMs) to 
autonomously browse the internet. It leverages tools like Playwright for 
browser automation and LangChain for LLM integration to perform tasks such as 
web scraping and content summarization

> [!WARNING]
> I use this for personal tasks - things might break! 

## Features
1. **Autonomous Web Browsing:** Uses an LLM agent to interact with web pages.
1. **Web Scraping:** Extracts specific data from web pages, including handling dynamic content and CAPTCHAs.
1. **LLM Querying:** Integrates with various LLMs (OpenAI, Anthropic, Google Gemini, Ollama) to process scraped data and generate responses.
1. **Task Management:** Defines and executes tasks such as browsing and scraping based on configurations.
1. **Data Handling:** Uses MongoDB to store prompts, context, and results.
1. **Reporting:** Posts LLM-generated responses to platforms like Discord using webhooks.

## Setup and Installation
1. Clone this repository.
2. Prerequisites:
    - Python 3.11
    - MongoDB
3. Create a Python virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate    # Unix/Linux
venv\Scripts\activate       # Windows
```
4. Install the required packages:
```bash
pip install -r requirements.txt
```
5. Configuration:
    - Create a `.env` file in the root directory and set the required environment variables (see `.env.example`).
    - Set up MongoDB and create a database named `llm_browser`.
    - Create collections for `prompts`, `context`, and `results` in the `llm_browser` database.
6. Run `main.py` to start the application.

## Demo
In the video below, the model was tasked with adding grocery items to cart, and checking out.

[![AI Did My Groceries](https://github.com/user-attachments/assets/d9359085-bde6-41d4-aa4e-6520d0221872)](https://www.youtube.com/watch?v=L2Ya9PYNns8)

## Adding a Prompt
Use mongo-express to add a prompt. 

Alternative, you can use the terminal.

```bash
use llm_browser

db.prompts.insertOne( { 
    task: "scrape", 
    title: "Prompt Title",
    url: "url_to_scrape",
    prompt: "This is the prompt and return to me the results as a \
    markdown:\n\n \
    result format: # <title> \n <entity> \n <summary>"
} )
```

## Running Tests
To run all tests:
```bash
pytest -vs
```

To run a specific test case:
```bash
pytest -vs tests/test_browser.py::test_fetch_linkedin
```