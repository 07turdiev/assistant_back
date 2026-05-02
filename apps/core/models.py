"""Shared abstract models."""
import uuid

from django.db import models
from django.utils import timezone

from .middleware import get_current_user


class AuditMixin(models.Model):
    """UUID PK + audit fields. Pre-save signal `created_by`/`updated_by`'ni to'ldiradi."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )
    updated_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        now = timezone.now()
        # `_state.adding` ishlatamiz — UUID default(uuid4) tufayli `pk` doim set bo'ladi.
        is_new = self._state.adding
        if is_new:
            if user and getattr(user, 'is_authenticated', False):
                self.created_by = user
                self.updated_by = user
            self.created_at = now
        elif user and getattr(user, 'is_authenticated', False):
            self.updated_by = user
        self.updated_at = now
        super().save(*args, **kwargs)
