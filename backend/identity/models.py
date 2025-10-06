import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from common.models import BaseModel

class UserManager(BaseUserManager):
    """Manager for custom user model with email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError(_('The Email must be set'))

        # If username is not provided, generate a unique one from the email.
        if 'username' not in extra_fields:
            username = email.split('@')[0]
            # Ensure username is unique
            original_username = username
            counter = 1
            while self.model.objects.filter(username=username).exists():
                username = f"{original_username}_{get_random_string(4)}"
            extra_fields['username'] = username

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        # Ensure username is set for superuser creation.
        if 'username' not in extra_fields:
            username = email.split('@')[0]
            # Ensure username is unique
            original_username = username
            counter = 1
            while self.model.objects.filter(username=username).exists():
                username = f"{original_username}_{get_random_string(4)}"
            extra_fields['username'] = username

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model where email is the primary identifier.
    Uses UUID for the primary key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    username = models.CharField(_('username'), max_length=150, unique=True, help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'))
    full_name = models.CharField(_('full name'), max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Add related_name to resolve clashes with the default User model
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="identity_user_set",  # Unique related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="identity_user_set",  # Unique related_name
        related_query_name="user",
    )
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    def __str__(self):
        return self.email

class ApiClient(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="api_clients")
    name = models.CharField(max_length=120)
    key = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)

class OAuthProvider(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="oauth_providers")
    kind = models.CharField(max_length=20)
    config = models.JSONField(default=dict, blank=True)
