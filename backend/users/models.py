"""
Django models for users app.
"""
import uuid
from django.db import models


class User(models.Model):
    """User model for storing user information."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    cpf = models.CharField(max_length=20)
    account_provider = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    picture = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.cpf})"
