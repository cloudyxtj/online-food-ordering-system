"""Audit logging service.

Keeps business logic for audit trail separate from views.
FR3: Every INSERT/UPDATE/DELETE on key entities is logged.
"""
from datetime import datetime, timezone
from app import db
from app.models import AuditLog


def log_action(user_id, action_type, description, entity_type, entity_id=None):
    """Create an audit log entry."""
    log = AuditLog(
        user_id=user_id,
        action_type=action_type,
        action_description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(log)
