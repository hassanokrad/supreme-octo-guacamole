"""Deprecated compatibility wrapper.

Use ``src.store`` directly for canonical persistence functions.
"""

from src.store import (
    admin_report,
    create_checkout_session,
    get_user,
    increment_root_hits,
    init_db,
    save_payment,
    set_paid_status,
    track_event,
    update_checkout_session_status,
    upsert_user,
)

__all__ = [
    "admin_report",
    "create_checkout_session",
    "get_user",
    "increment_root_hits",
    "init_db",
    "save_payment",
    "set_paid_status",
    "track_event",
    "update_checkout_session_status",
    "upsert_user",
]
