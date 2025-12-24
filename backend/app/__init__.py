"""Top level package for the MoniTe Web backend.

This package exposes the FastAPI application and initialises
common infrastructure such as the database engine, router
registration and the scheduler. All other modules should live
under this package to keep the import graph tidy.

See :mod:`monite_web.backend.app.main` for the application entrypoint.
"""

from .main import app  # noqa: F401