from .models import AuditLog


def log_action(user, action, resource, resource_id="", metadata=None):
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        resource=resource,
        resource_id=str(resource_id),
        metadata=metadata or {},
    )
