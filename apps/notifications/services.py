from django.utils import timezone


def mark_read(notification):
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return notification


def mark_all_read(queryset):
    return queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
