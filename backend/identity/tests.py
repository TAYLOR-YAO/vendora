from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserRegistrationTest(APITestCase):
    """
    Test suite for the user registration endpoint.
    """

    def setUp(self):
        """
        Define the URL for the registration endpoint.
        """
        self.register_url = reverse("auth_register")

    def test_user_registration_success(self):
        """
        Ensure we can create a new user account with valid data.
        """
        data = {
            "email": "testuser@example.com",
            "full_name": "Test User",
            "password": "some-strong-password-123",
            "password2": "some-strong-password-123",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)

        user = User.objects.get()
        self.assertEqual(user.email, data["email"])
        self.assertEqual(user.full_name, data["full_name"])
        self.assertTrue(user.check_password(data["password"]))
        self.assertFalse(user.is_staff)

    def test_user_registration_password_mismatch(self):
        """
        Ensure registration fails if the 'password' and 'password2' fields do not match.
        """
        data = {
            "email": "testuser@example.com",
            "full_name": "Test User",
            "password": "some-strong-password-123",
            "password2": "a-different-password",
        }
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("password", response.data)
        self.assertEqual(response.data["password"][0], "Password fields didn't match.")

    def test_user_registration_email_already_exists(self):
        """
        Ensure registration fails if the email is already taken.
        """
        # Create a user with the email we're about to test
        User.objects.create_user(email="testuser@example.com", full_name="Existing User", password="password123")

        data = {
            "email": "testuser@example.com",
            "full_name": "New User",
            "password": "some-strong-password-123",
            "password2": "some-strong-password-123",
        }
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1) # Ensure no new user was created
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"][0], "user with this email address already exists.")