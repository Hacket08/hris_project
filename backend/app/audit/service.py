import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    entity_name: str,
    entity_id: str,
    changed_by: uuid.UUID | None,
    field_changed: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
) -> None:
    """The single write path for audit_log. Every module's service layer calls
    this — never write to AuditLog directly, and never call it from a router
    (routers may not have the transaction context service layers rely on for
    atomicity with the change being audited).
    """
    db.add(
        AuditLog(
            entity_name=entity_name,
            entity_id=entity_id,
            changed_by=changed_by,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
    )
