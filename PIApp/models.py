from django.conf import settings
from django.db import models


class AthleteProfile(models.Model):
    BUDGET_CHOICES = (
        ("barato", "Barato"),
        ("economico", "Económico"),
        ("caro", "Caro"),
    )
    ACTIVITY_CHOICES = (
        ("siempre", "Hago deporte siempre"),
        ("a_veces", "Hago deporte a veces"),
        ("pocas_veces", "Hago deporte pocas veces"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="athlete_profile",
    )
    weight_kg = models.FloatField("peso en kilogramos")
    height_cm = models.FloatField("altura en centímetros")
    food_budget = models.CharField(
        "presupuesto de alimentos", max_length=12, choices=BUDGET_CHOICES,
        default="economico",
    )
    activity_frequency = models.CharField(
        "frecuencia de actividad",
        max_length=12,
        choices=ACTIVITY_CHOICES,
        blank=True,
    )
    sport_1 = models.CharField("deporte 1", max_length=40, blank=True)
    sport_2 = models.CharField("deporte 2", max_length=40, blank=True)
    sport_3 = models.CharField("deporte 3", max_length=40, blank=True)

    def __str__(self):
        return f"Perfil de {self.user.email}"

    @property
    def sports(self):
        return [sport for sport in (self.sport_1, self.sport_2, self.sport_3) if sport]
