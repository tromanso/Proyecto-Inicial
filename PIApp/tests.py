from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import AthleteProfile
from .views import _bmi_category


class BMICategoryTests(SimpleTestCase):
    def test_adult_bmi_category_boundaries(self):
        cases = (
            (18.49, "Por debajo del rango saludable"),
            (18.5, "Rango saludable"),
            (24.99, "Rango saludable"),
            (25, "Sobrepeso"),
            (29.99, "Sobrepeso"),
            (30, "Obesidad"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_bmi_category(value), expected)


class AthleteFlowTests(TestCase):
    def test_homepage_introduces_app_and_links_to_login(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pequeños hábitos. Una vida más activa.")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, "Organiza tu actividad")
        self.assertContains(response, "/static/PIApp/fitapp-cartoon.svg")

    def test_login_page_remains_available_at_login_url(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar sesión")
        self.assertContains(response, 'class="login-background"')
        self.assertContains(response, 'class="login-background-image"')
        self.assertContains(response, "/static/PIApp/login-background.webp")
        self.assertContains(response, 'id="email"')

    def test_sport_guides_match_profile_sports(self):
        user = User.objects.create_user(
            username="guides@example.com",
            email="guides@example.com",
            password="secure-pass-123",
        )
        AthleteProfile.objects.create(
            user=user,
            weight_kg=70,
            height_cm=175,
            food_budget="economico",
            sport_1="futbol",
            sport_2="tenis",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("sport_guides"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guías para tus deportes")
        self.assertContains(response, "Fútbol")
        self.assertContains(response, "Tenis")
        self.assertContains(response, "Australian Institute of Sport")
        self.assertContains(response, "sportsmedtoday.com/soccer-ct-9.htm")
        self.assertNotContains(response, "Basquetbol")

    def test_sport_guides_offer_activity_setup_when_profile_has_no_sports(self):
        user = User.objects.create_user(
            username="noguides@example.com",
            email="noguides@example.com",
            password="secure-pass-123",
        )
        AthleteProfile.objects.create(
            user=user,
            weight_kg=70,
            height_cm=175,
            food_budget="economico",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("sport_guides"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún no has indicado qué deportes practicas")
        self.assertContains(response, reverse("edit_profile") + "?section=activity")

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
        for sport in ("Fútbol", "Voleibol", "Básquetbol", "Tenis", "Boxeo"):
            self.assertContains(response, sport)
        response = self.client.post(
            reverse("activity_setup"),
            {
                "activity_frequency": "siempre",
                "sport_1": "futbol",
                "sport_2": "tenis",
                "sport_3": "",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.sports, ["futbol", "tenis"])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendario de comidas")
        self.assertContains(response, "Tu IMC")
        self.assertContains(response, reverse("sport_guides"))
        self.assertContains(response, "Rango saludable")
        self.assertContains(response, "según la edad y el sexo")
        self.assertContains(response, "Consulta la referencia de la OMS")
        self.assertContains(response, "Fútbol")
        self.assertContains(response, "Desayuno")

    def test_calendar_download_returns_a_pdf_attachment(self):
        user = User.objects.create_user(
            username="calendar@example.com",
            email="calendar@example.com",
            password="secure-pass-123",
        )
        AthleteProfile.objects.create(
            user=user,
            weight_kg=70,
            height_cm=175,
            food_budget="economico",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("download_calendar"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

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
                "sport_1": "voleibol",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.activity_frequency, "pocas_veces")
        self.assertEqual(profile.sport_1, "voleibol")

    def test_activity_rejects_sports_outside_the_selection_list(self):
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
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("activity_setup"),
            {
                "activity_frequency": "siempre",
                "sport_1": "natacion",
                "sport_2": "",
                "sport_3": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecciona deportes de la lista.")
        profile.refresh_from_db()
        self.assertEqual(profile.sports, [])

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
