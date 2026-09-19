import pytest
from django.urls import reverse
from accounts.models import User
from accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_signup_creates_user(client):
    url = reverse("signup")
    payload = {
        "username": "newuser",
        "password1": "strongpassword123",
        "password2": "strongpassword123",
    }
    response = client.post(url, payload)
    assert response.status_code == 302
    assert response.url == reverse("login")
    assert User.objects.filter(username="newuser").exists()


@pytest.mark.django_db
def test_signup_rejects_mismatched_passwords(client):
    url = reverse("signup")
    payload = {
        "username": "mismatchuser",
        "password1": "password123",
        "password2": "mismatchedpass456",
    }
    response = client.post(url, payload)
    assert response.status_code == 200
    assert not User.objects.filter(username="mismatchuser").exists()
    assert "password2" in response.context["form"].errors or "__all__" in response.context["form"].errors


@pytest.mark.django_db
def test_login_success_redirects_to_dashboard(client):
    user = UserFactory(username="authuser")
    url = reverse("login")
    response = client.post(url, {"username": "authuser", "password": "testpass123"})
    assert response.status_code == 302
    assert response.url == reverse("dashboard")
    assert int(client.session["_auth_user_id"]) == user.pk


@pytest.mark.django_db
def test_login_failure_shows_error(client):
    UserFactory(username="authuser")
    url = reverse("login")
    response = client.post(url, {"username": "authuser", "password": "wrongpassword"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert response.context["form"].errors


@pytest.mark.django_db
def test_logout_clears_session(client):
    user = UserFactory(username="logoutuser")
    client.force_login(user)

    dashboard_url = reverse("dashboard")
    resp_before = client.get(dashboard_url)
    assert resp_before.status_code == 200

    logout_url = reverse("logout")
    resp_logout = client.post(logout_url)
    assert resp_logout.status_code in (302, 200)

    resp_after = client.get(dashboard_url)
    assert resp_after.status_code == 302
    assert reverse("login") in resp_after.url


@pytest.mark.django_db
def test_login_page_includes_frontend_assets(client):
    url = reverse("login")
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "vendor/htmx.min.js" in content
    assert "vendor/alpine.min.js" in content
    assert "vendor/chart.min.js" in content
    assert "main.css" in content


@pytest.mark.django_db
def test_otp_setup_requires_login(client):
    url = reverse("otp_setup")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_otp_setup_get_renders_qr_code(client):
    user = UserFactory()
    client.force_login(user)

    url = reverse("otp_setup")
    response = client.get(url)
    assert response.status_code == 200
    assert "qr_b64" in response.context
    assert "data:image/png;base64," in response.content.decode()


@pytest.mark.django_db
def test_otp_setup_post_valid_token_confirms_device(client):
    from unittest.mock import patch

    user = UserFactory()
    client.force_login(user)

    url = reverse("otp_setup")
    # First GET creates the device
    client.get(url)

    with patch("django_otp.plugins.otp_totp.models.TOTPDevice.verify_token", return_value=True):
        response = client.post(url, {"token": "123456"})

    assert response.status_code == 302
    assert response.url == reverse("dashboard")

    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.get(user=user)
    assert device.confirmed is True


@pytest.mark.django_db
def test_otp_setup_post_invalid_token_shows_error(client):
    from unittest.mock import patch
    from django_otp.plugins.otp_totp.models import TOTPDevice

    user = UserFactory()
    client.force_login(user)

    url = reverse("otp_setup")
    client.get(url)

    with patch("django_otp.plugins.otp_totp.models.TOTPDevice.verify_token", return_value=False):
        response = client.post(url, {"token": "000000"})

    assert response.status_code == 200
    assert "Invalid 6-digit verification code" in response.content.decode()

    device = TOTPDevice.objects.get(user=user)
    assert device.confirmed is False


@pytest.mark.django_db
def test_otp_setup_preserves_and_redirects_to_next_url(client):
    from unittest.mock import patch

    user = UserFactory()
    client.force_login(user)

    target_next = "/investments/connect/"
    url = f"{reverse('otp_setup')}?next={target_next}"
    client.get(url)

    with patch("django_otp.plugins.otp_totp.models.TOTPDevice.verify_token", return_value=True):
        response = client.post(url, {"token": "654321", "next": target_next})

    assert response.status_code == 302
    assert response.url == target_next


@pytest.mark.django_db
def test_otp_setup_shows_confirmed_badge_when_already_verified(client):
    from django_otp.plugins.otp_totp.models import TOTPDevice

    user = UserFactory()
    client.force_login(user)
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)

    url = reverse("otp_setup")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "2FA Currently Active" in content
    assert "Enter a 6-digit code" in content


@pytest.mark.django_db
def test_email_uniqueness_enforced():
    from django.db import IntegrityError

    User.objects.create_user(username="user1", email="duplicate@example.com", password="password123")
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="user2", email="duplicate@example.com", password="password123")


