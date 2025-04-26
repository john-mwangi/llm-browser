"""Task definitions (TaskType Enum and task execution logic/runners"""

from enum import Enum


class TaskType(Enum):
    """Enum representing different types of tasks that can be performed"""

    BROWSE = "browse"
    SCRAPE = "scrape"
