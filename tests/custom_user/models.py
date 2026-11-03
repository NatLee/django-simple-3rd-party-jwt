from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class EmailUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(email, password, is_staff=True, is_superuser=True, **extra_fields)


class EmailUser(AbstractBaseUser, PermissionsMixin):
    """The e-mail address is the login name; there is no username, first_name or last_name."""

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = EmailUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
