import calendar
from math import isfinite

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import AthleteProfile


MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

MEALS = {
    "barato": [
        ("Avena con plátano", "Lentejas con arroz", "Huevo con verduras"),
        ("Pan con huevo y fruta", "Frijoles con tortillas y ensalada", "Sopa de verduras con queso"),
        ("Yogur con avena", "Arroz con atún y verduras", "Tostadas de frijoles"),
        ("Avena con manzana", "Pasta con verduras y huevo", "Quesadillas con frijoles"),
        ("Huevo con tortillas y fruta", "Garbanzos con arroz", "Sándwich de queso y tomate"),
        ("Licuado de plátano y avena", "Papa con huevo y verduras", "Ensalada de lentejas"),
        ("Pan con frijoles y fruta", "Arroz con pollo y verduras", "Sopa de frijoles"),
    ],
    "economico": [
        ("Yogur con fruta y avena", "Pollo con arroz y verduras", "Tostadas de aguacate y huevo"),
        ("Huevos con pan integral", "Pescado con papa y ensalada", "Sopa de verduras con queso"),
        ("Avena con fruta y nueces", "Carne magra con arroz y verduras", "Ensalada de garbanzos"),
        ("Pan integral con queso y fruta", "Pasta con pollo y verduras", "Tacos de frijoles y verduras"),
        ("Yogur con granola y fruta", "Lentejas con huevo y ensalada", "Sándwich de pollo"),
        ("Huevo con verduras y tortillas", "Atún con papa y ensalada", "Quesadillas con champiñones"),
        ("Avena con plátano", "Pollo con camote y verduras", "Ensalada de frijoles y queso"),
    ],
    "caro": [
        ("Yogur griego con fruta y nueces", "Salmón con quinoa y verduras", "Ensalada de pollo y aguacate"),
        ("Tostadas integrales con aguacate y huevo", "Bowl de quinoa con pavo", "Crema de verduras con queso"),
        ("Avena con frutos rojos y almendras", "Pescado con camote y ensalada", "Ensalada de garbanzos y queso"),
        ("Omelette de verduras y fruta", "Carne magra con quinoa", "Tacos de pescado y col"),
        ("Yogur griego con granola", "Pollo con arroz integral y verduras", "Sopa de lentejas y ensalada"),
        ("Pan integral con huevo y aguacate", "Camarones con pasta y verduras", "Ensalada de atún"),
        ("Avena con fruta y semillas", "Pavo con papa y verduras", "Quesadillas de champiñones y ensalada"),
    ],
}


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = User.objects.filter(email__iexact=email).first()
        authenticated_user = authenticate(
            request, username=user.username if user else email, password=password
        )
        if authenticated_user:
            auth_login(request, authenticated_user)
            if hasattr(authenticated_user, "athlete_profile"):
                return redirect("dashboard")
            return redirect("activity_setup")
        messages.error(request, "El correo o la contraseña no son correctos.")

    return render(request, "login.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        weight = request.POST.get("weight", "")
        height = request.POST.get("height", "")
        budget = request.POST.get("budget", "")
        errors = []

        if not email or "@" not in email:
            errors.append("Ingresa un correo válido.")
        if len(email) > 150:
            errors.append("El correo no puede superar 150 caracteres.")
        if User.objects.filter(email__iexact=email).exists():
            errors.append("Ya existe una cuenta con ese correo.")
        try:
            validate_password(password, User(username=email, email=email))
        except ValidationError as error:
            errors.extend(error.messages)

        try:
            weight_value = float(weight)
            if not isfinite(weight_value) or not 25 <= weight_value <= 300:
                errors.append("El peso debe estar entre 25 y 300 kg.")
        except (TypeError, ValueError):
            weight_value = None
            errors.append("Ingresa un peso válido en kilogramos.")

        try:
            height_value = float(height)
            if not isfinite(height_value) or not 100 <= height_value <= 250:
                errors.append("La altura debe estar entre 100 y 250 cm.")
        except (TypeError, ValueError):
            height_value = None
            errors.append("Ingresa una altura válida en centímetros.")

        if budget not in dict(AthleteProfile.BUDGET_CHOICES):
            errors.append("Selecciona una opción de presupuesto.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, "signup.html", request.POST)

        with transaction.atomic():
            user = User.objects.create_user(
                username=email, email=email, password=password
            )
            AthleteProfile.objects.create(
                user=user,
                weight_kg=weight_value,
                height_cm=height_value,
                food_budget=budget,
            )
        auth_login(request, user)
        return redirect("activity_setup")

    return render(request, "signup.html")


@login_required
def activity_setup(request):
    profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        frequency = request.POST.get("activity_frequency", "")
        sports = [request.POST.get(f"sport_{index}", "").strip() for index in range(1, 4)]
        if frequency not in dict(AthleteProfile.ACTIVITY_CHOICES):
            messages.error(request, "Selecciona con qué frecuencia haces deporte.")
            return render(request, "activity.html", {"profile": profile})

        profile.activity_frequency = frequency
        profile.sport_1, profile.sport_2, profile.sport_3 = sports
        profile.save()
        return redirect("dashboard")

    return render(request, "activity.html", {"profile": profile})


@login_required
def dashboard(request):
    profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    month_days = calendar.Calendar(firstweekday=0).monthdatescalendar(
        today.year, today.month
    )
    meals = MEALS[profile.food_budget or "economico"]
    calendar_weeks = []
    for week in month_days:
        calendar_weeks.append(
            [
                {
                    "date": day,
                    "in_month": day.month == today.month,
                    "meals": meals[day.weekday()],
                }
                for day in week
            ]
        )

    height_m = profile.height_cm / 100
    bmi = round(profile.weight_kg / (height_m * height_m), 1)
    if bmi < 18.5:
        bmi_label = "Por debajo del rango de referencia"
    elif bmi < 25:
        bmi_label = "Dentro del rango de referencia"
    elif bmi < 30:
        bmi_label = "Por encima del rango de referencia"
    else:
        bmi_label = "Rango alto de referencia"

    return render(
        request,
        "dashboard.html",
        {
            "profile": profile,
            "bmi": bmi,
            "bmi_label": bmi_label,
            "calendar_weeks": calendar_weeks,
            "month_name": f"{MONTHS_ES[today.month - 1]} {today.year}",
        },
    )


@login_required
def edit_profile(request):
    profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
    section = request.GET.get("section", "profile")
    if section not in ("profile", "activity"):
        section = "profile"

    if request.method == "POST":
        section = request.POST.get("section", "profile")
        if section == "profile":
            email = request.POST.get("email", "").strip().lower()
            weight = request.POST.get("weight", "")
            height = request.POST.get("height", "")
            budget = request.POST.get("budget", "")
            errors = []

            if not email or "@" not in email:
                errors.append("Ingresa un correo válido.")
            if len(email) > 150:
                errors.append("El correo no puede superar 150 caracteres.")
            if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
                errors.append("Ya existe una cuenta con ese correo.")
            if User.objects.filter(username=email).exclude(pk=request.user.pk).exists():
                errors.append("Ese correo ya está asociado a otra cuenta.")
            try:
                weight_value = float(weight)
                if not isfinite(weight_value) or not 25 <= weight_value <= 300:
                    errors.append("El peso debe estar entre 25 y 300 kg.")
            except (TypeError, ValueError):
                weight_value = None
                errors.append("Ingresa un peso válido en kilogramos.")
            try:
                height_value = float(height)
                if not isfinite(height_value) or not 100 <= height_value <= 250:
                    errors.append("La altura debe estar entre 100 y 250 cm.")
            except (TypeError, ValueError):
                height_value = None
                errors.append("Ingresa una altura válida en centímetros.")
            if budget not in dict(AthleteProfile.BUDGET_CHOICES):
                errors.append("Selecciona una opción de presupuesto.")

            if not errors:
                request.user.email = email
                request.user.username = email
                request.user.save(update_fields=["email", "username"])
                profile.weight_kg = weight_value
                profile.height_cm = height_value
                profile.food_budget = budget
                profile.save()
                messages.success(request, "Tu perfil se actualizó.")
                return redirect("dashboard")

            for error in errors:
                messages.error(request, error)
        elif section == "activity":
            frequency = request.POST.get("activity_frequency", "")
            if frequency in dict(AthleteProfile.ACTIVITY_CHOICES):
                profile.activity_frequency = frequency
                profile.sport_1 = request.POST.get("sport_1", "").strip()
                profile.sport_2 = request.POST.get("sport_2", "").strip()
                profile.sport_3 = request.POST.get("sport_3", "").strip()
                profile.save()
                messages.success(request, "Tu actividad se actualizó.")
                return redirect("dashboard")
            messages.error(request, "Selecciona con qué frecuencia haces deporte.")

    return render(
        request,
        "edit_profile.html",
        {"profile": profile, "section": section},
    )


def logout_view(request):
    auth_logout(request)
    return redirect("login")
