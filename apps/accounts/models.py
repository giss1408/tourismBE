from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid


class AppUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if email:
            email = self.normalize_email(email)
        elif not extra.get('firebase_uid'):
            # Email is required for email/password accounts only
            raise ValueError('Email is required for email/password accounts.')
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class AppUser(AbstractBaseUser, PermissionsMixin):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True, null=True, blank=True)
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True, db_index=True)
    display_name = models.CharField(max_length=150, blank=True)
    photo_url = models.URLField(blank=True)
    provider = models.CharField(max_length=50, default='email')
    # Language for emails and notifications: fr, en or de.
    language = models.CharField(max_length=5, default='fr')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = AppUserManager()

    class Meta:
        verbose_name = 'User'

    def __str__(self):
        return self.email
