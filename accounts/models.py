from datetime import date
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email", unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email


class HealthProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="health_profile")
    birth_date = models.DateField("дата рождения", null=True, blank=True)
    height_cm = models.DecimalField(
        "рост, см",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("30"))],
    )

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )


class BodyWeightMeasurement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="body_weights")
    weight_kg = models.DecimalField(
        "вес, кг",
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1"))],
    )
    measured_at = models.DateTimeField("дата и время")
    note = models.CharField("заметка", max_length=300, blank=True)

    class Meta:
        ordering = ["-measured_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "measured_at"], name="unique_weight_time_per_user"
            )
        ]
