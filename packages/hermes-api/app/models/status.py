"""Status values shared by database models and API filters."""

from typing import Literal

DownloadState = Literal[
    "pending", "downloading", "processing", "completed", "failed", "cancelled"
]
HistoryStatus = Literal["completed", "failed", "cancelled"]
