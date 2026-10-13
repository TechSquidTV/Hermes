# Third-party typing boundaries

The locked yt-dlp package does not ship type information. These partial stubs
describe the interfaces Hermes uses, including its request handlers, native
downloaders, extraction results, and extractor discovery. Mypy reads this
directory through `mypy_path` in `pyproject.toml`; it is not runtime code.

The transport interfaces are exercised by real yt-dlp HTTP, redirect, HLS, TLS,
and local media-conversion tests. Dynamic yt-dlp option and metadata dictionaries
remain explicit at the external boundary. When updating yt-dlp, compare these
signatures with the installed source and run the backend checks and tests.

Celery and Kombu imports have narrowly scoped missing-import overrides. Celery's
task decorator is typed through `app/tasks/types.py`, which preserves each task's
parameters and return type while returning the actual Celery task object.
