from django.db import models

from apps.accounts.models import User


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=50)
    resource = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"], name="idx_audit_log_created")]

    def __str__(self):
        return f"{self.action} {self.resource}:{self.resource_id}"
