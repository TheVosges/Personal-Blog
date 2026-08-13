"""Authentication helper module for the Personal Blog application.

Provides session-based admin authentication and route protection decorators.
"""

from __future__ import annotations

import hmac
import os
from functools import wraps
from typing import Any, Callable

from flask import flash, redirect, request, session, url_for

# Configurable admin credentials (can be set via environment variables)
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def verify_credentials(username: str, password: str) -> bool:
    """Verify submitted credentials against configured admin credentials."""
    expected_user = os.environ.get("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
    expected_pass = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    user_match = hmac.compare_digest(username.strip(), expected_user.strip())
    pass_match = hmac.compare_digest(password, expected_pass)
    return user_match and pass_match


def is_authenticated() -> bool:
    """Check if the current session belongs to an authenticated admin."""
    return session.get("is_admin", False) is True


def login_admin(username: str) -> None:
    """Mark session as authenticated admin."""
    session["is_admin"] = True
    session["username"] = username


def logout_admin() -> None:
    """Clear admin session credentials."""
    session.pop("is_admin", None)
    session.pop("username", None)


def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to require admin authentication for protected views."""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not is_authenticated():
            flash("Please log in with admin privileges to access this page.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)

    return decorated_function
