from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model for Planning Pocket.
    We extend AbstractUser to allow future customizations easily.
    """
    pass
