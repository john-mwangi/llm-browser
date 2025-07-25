"""Handles loading .env, environment variables, constants (browser args, paths, model names)"""

from pathlib import Path
from typing import NamedTuple

ROOT_DIR = Path(__file__).parent.parent
results_dir = ROOT_DIR / "results"

browser_args = [
    "--window-size=1300,570",
    "--window-position=000,000",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=site-per-process",
    "--disable-setuid-sandbox",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--use-gl=egl",
    "--disable-blink-features=AutomationControlled",
    "--disable-background-networking",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=Translate",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--enable-automation",
    "--password-store=basic",
    "--use-mock-keychain",
    "--hide-scrollbars",
    "--mute-audio",
    "--ignore-certificate-errors",
    "--enable-webgl",
]


class RateLimit(NamedTuple):
    """Rate limit configuration for API requests (RPS)"""

    gemini_2_0: float = 15 / 60
    discord: int = 50
    min_delay: float = 0.1
