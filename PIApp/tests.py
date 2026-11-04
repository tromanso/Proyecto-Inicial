from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import AthleteProfile


class AthleteFlowTests(TestCase):
    def test_signup_activity_and_dashboard_flow(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "athlete@example.com",
                "password": "secure-pass-123",
                "weight": "70",
                "height": "175",
                "budget": "economico",
            },
        )

        self.assertRedirects(response, reverse("activity_setup"))
        user = User.objects.get(email="athlete@example.com")
        self.assertTrue(self.client.session.get("_auth_user_id"))
        profile = AthleteProfile.objects.get(user=user)
        self.assertEqual(profile.food_budget, "economico")

        response = self.client.get(reverse("activity_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hago deporte siempre")
        response = self.client.post(
            reverse("activity_setup"),
            {
                "activity_frequency": "siempre",
                "sport_1": "Fútbol",
                "sport_2": "Natación",
                "sport_3": "",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.sports, ["Fútbol", "Natación"])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendario de comidas")
        self.assertContains(response, "Tu IMC")
        self.assertContains(response, "Natación")
        self.assertContains(response, "Desayuno")

    def test_login_and_profile_edits(self):
        user = User.objects.create_user(
            username="athlete@example.com",
            email="athlete@example.com",
            password="secure-pass-123",
        )
        profile = AthleteProfile.objects.create(
            user=user,
            weight_kg=70,
            height_cm=175,
            food_budget="economico",
            activity_frequency="a_veces",
        )
        response = self.client.post(
            reverse("login"),
            {"email": "athlete@example.com", "password": "secure-pass-123"},
        )
        self.assertRedirects(response, reverse("dashboard"))

        response = self.client.post(
            f"{reverse('edit_profile')}?section=profile",
            {
                "section": "profile",
                "email": "new@example.com",
                "weight": "72",
                "height": "176",
                "budget": "barato",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        profile.refresh_from_db()
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.username, "new@example.com")
        self.assertEqual(profile.weight_kg, 72)
        self.assertEqual(profile.food_budget, "barato")

        response = self.client.post(
            f"{reverse('edit_profile')}?section=activity",
            {
                "section": "activity",
                "activity_frequency": "pocas_veces",
                "sport_1": "Ciclismo",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.activity_frequency, "pocas_veces")
        self.assertEqual(profile.sport_1, "Ciclismo")

    def test_invalid_signup_does_not_create_account(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "bad@example.com",
                "password": "short",
                "weight": "nan",
                "height": "175",
                "budget": "economico",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="bad@example.com").exists())
