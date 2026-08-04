from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import BodyWeightMeasurement, HealthProfile, User


@pytest.mark.django_db
def test_registration_uses_email_and_logs_user_in(client):
    response = client.post(
        reverse("register"),
        {
            "email": "athlete@example.com",
            "password1": "A-very-long-test-password-42",
            "password2": "A-very-long-test-password-42",
        },
    )
    assert response.status_code == 302
    assert User.objects.filter(email="athlete@example.com").exists()
    assert client.get(reverse("dashboard")).status_code == 200


@pytest.mark.django_db
def test_health_data_is_private(client):
    owner = User.objects.create_user("owner@example.com", "test-password-123")
    stranger = User.objects.create_user("stranger@example.com", "test-password-123")
    item = BodyWeightMeasurement.objects.create(
        user=owner, weight_kg="81.25", measured_at=timezone.now()
    )
    client.force_login(stranger)
    assert client.get(reverse("health")).status_code == 200
    client.post(reverse("delete_weight", args=[item.pk]))
    assert BodyWeightMeasurement.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_age_is_calculated_from_birth_date():
    user = User.objects.create_user("age@example.com", "test-password-123")
    today = date.today()
    profile = HealthProfile.objects.create(
        user=user, birth_date=today - timedelta(days=365 * 30 + 7)
    )
    assert profile.age in {29, 30}
