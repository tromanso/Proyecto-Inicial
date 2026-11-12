import calendar
from io import BytesIO
from math import isfinite
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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

NUTRITION_GUIDE = {
    "title": "Nutrición para el entrenamiento y la competencia",
    "organization": "Australian Institute of Sport",
    "description": "Módulos sobre alimentación, hidratación y recuperación para deportistas.",
    "url": "https://www.ausport.gov.au/ais/nutrition/performance-nutrition-hq-modules",
}

SPORT_GUIDES = {
    "futbol": {
        "description": "Información médica sobre lesiones y prevención en fútbol.",
        "title": "Salud y prevención en fútbol",
        "organization": "Sports Medicine Today · AMSSM",
        "url": "https://www.sportsmedtoday.com/soccer-ct-9.htm",
    },
    "voleibol": {
        "description": "Recursos de educación y desarrollo integral para la comunidad del voleibol.",
        "title": "Educación y desarrollo en voleibol",
        "organization": "USA Volleyball",
        "url": "https://usavolleyball.org/resources/",
    },
    "basquetbol": {
        "description": "Introducción a salud y seguridad para la práctica del baloncesto.",
        "title": "Salud y seguridad en baloncesto",
        "organization": "USA Basketball",
        "url": "https://www.usab.com/health",
    },
    "tenis": {
        "description": "Información sobre lesiones, factores de riesgo y prevención en tenis.",
        "title": "Salud y prevención en tenis",
        "organization": "Sports Medicine Today · AMSSM",
        "url": "https://www.sportsmedtoday.com/tennis-ct-73.htm",
    },
    "boxeo": {
        "description": "Referencia médica para artes marciales y deportes de combate; no es exclusiva del boxeo.",
        "title": "Cuidados en deportes de combate",
        "organization": "Sports Medicine Today · AMSSM",
        "url": "https://www.sportsmedtoday.com/martial-arts-ct-31.htm",
    },
}


def _activity_context(profile):
    sport_choices = list(AthleteProfile.SPORT_CHOICES)
    known_sports = {value for value, _ in sport_choices}
    for sport in profile.sports:
        if sport not in known_sports:
            sport_choices.append((sport, sport))
    return {"profile": profile, "sport_choices": sport_choices}


def _posted_sports(request):
    return [request.POST.get(f"sport_{index}", "").strip() for index in range(1, 4)]


def _calendar_weeks(year, month, budget):
    meals = MEALS[budget or "economico"]
    return [
        [
            {
                "date": day,
                "in_month": day.month == month,
                "meals": meals[day.weekday()],
            }
            for day in week
        ]
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    ]


def _bmi_category(value):
    if value < 18.5:
        return "Por debajo del rango saludable"
    if value < 25:
        return "Rango saludable"
    if value < 30:
        return "Sobrepeso"
    return "Obesidad"


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


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
        sports = _posted_sports(request)
        allowed_sports = {
            value for value, _ in _activity_context(profile)["sport_choices"]
        }
        if frequency not in dict(AthleteProfile.ACTIVITY_CHOICES):
            messages.error(request, "Selecciona con qué frecuencia haces deporte.")
            return render(request, "activity.html", _activity_context(profile))
        if any(sport and sport not in allowed_sports for sport in sports):
            messages.error(request, "Selecciona deportes de la lista.")
            return render(request, "activity.html", _activity_context(profile))
        selected_sports = [sport for sport in sports if sport]
        if len(selected_sports) != len(set(selected_sports)):
            messages.error(request, "No selecciones el mismo deporte más de una vez.")
            return render(request, "activity.html", _activity_context(profile))

        profile.activity_frequency = frequency
        profile.sport_1, profile.sport_2, profile.sport_3 = sports
        profile.save()
        return redirect("dashboard")

    return render(request, "activity.html", _activity_context(profile))


@login_required
def dashboard(request):
    profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    calendar_weeks = _calendar_weeks(
        today.year, today.month, profile.food_budget
    )

    height_m = profile.height_cm / 100
    bmi_value = profile.weight_kg / (height_m * height_m)
    bmi = round(bmi_value, 1)
    bmi_label = _bmi_category(bmi_value)

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
def sport_guides(request):
    profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
    guides = []
    for sport, display_name in zip(profile.sports, profile.sports_display):
        guide = SPORT_GUIDES.get(sport)
        if guide:
            guides.append({"name": display_name, **guide})
        else:
            guides.append(
                {
                    "name": display_name,
                    "description": "Consulta información general sobre prevención de lesiones deportivas.",
                    "title": "Guías de prevención de lesiones",
                    "organization": "Sports Medicine Australia",
                    "url": "https://sma.org.au/resources/injury-fact-sheets/",
                }
            )
    return render(
        request,
        "sport_guides.html",
        {
            "sport_guides": guides,
            "nutrition_guide": NUTRITION_GUIDE,
        },
    )


@login_required
def download_calendar(request):
    profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    calendar_weeks = _calendar_weeks(
        today.year, today.month, profile.food_budget
    )
    month_name = f"{MONTHS_ES[today.month - 1]} {today.year}"
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=22,
        bottomMargin=22,
        title=f"Calendario de comidas - {month_name}",
    )
    title_style = ParagraphStyle(
        "CalendarTitle",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#1d3028"),
    )
    subtitle_style = ParagraphStyle(
        "CalendarSubtitle",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7972"),
    )
    weekday_style = ParagraphStyle(
        "CalendarWeekday",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )
    cell_style = ParagraphStyle(
        "CalendarCell",
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#1d3028"),
    )
    note_style = ParagraphStyle(
        "CalendarNote",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#6b7972"),
    )
    story = [
        Paragraph(f"Calendario de comidas · {month_name}", title_style),
        Paragraph(
            "Ideas de comidas según tu presupuesto: "
            f"{escape(profile.get_food_budget_display() or 'Económico')}",
            subtitle_style,
        ),
        Spacer(1, 10),
    ]
    weekdays = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
    table_data = [[Paragraph(day, weekday_style) for day in weekdays]]
    for week in calendar_weeks:
        row = []
        for day in week:
            day_color = "#89938d" if not day["in_month"] else "#245c45"
            meal_text = "<br/>".join(
                f"<b>{label}:</b> {escape(meal)}"
                for label, meal in zip(
                    ("Desayuno", "Comida", "Cena"), day["meals"]
                )
            )
            row.append(
                Paragraph(
                    f'<font color="{day_color}"><b>{day["date"].day}</b></font>'
                    f"<br/>{meal_text}",
                    cell_style,
                )
            )
        table_data.append(row)

    column_width = document.width / 7
    table = Table(
        table_data,
        colWidths=[column_width] * 7,
        repeatRows=1,
        hAlign="LEFT",
    )
    table_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#245c45")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce4dc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_index, week in enumerate(calendar_weeks, start=1):
        for column_index, day in enumerate(week):
            if not day["in_month"]:
                table_commands.append(
                    (
                        "BACKGROUND",
                        (column_index, row_index),
                        (column_index, row_index),
                        colors.HexColor("#f0f3ef"),
                    )
                )
    table.setStyle(TableStyle(table_commands))
    story.extend(
        [
            table,
            Spacer(1, 8),
            Paragraph(
                "Estas sugerencias son ejemplos y no sustituyen la orientación "
                "de un profesional de nutrición.",
                note_style,
            ),
        ]
    )
    document.build(story)

    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="calendario-comidas-{today:%Y-%m}.pdf"'
    )
    return response


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
            sports = _posted_sports(request)
            allowed_sports = {
                value for value, _ in _activity_context(profile)["sport_choices"]
            }
            selected_sports = [sport for sport in sports if sport]
            if (
                frequency in dict(AthleteProfile.ACTIVITY_CHOICES)
                and all(not sport or sport in allowed_sports for sport in sports)
                and len(selected_sports) == len(set(selected_sports))
            ):
                profile.activity_frequency = frequency
                profile.sport_1, profile.sport_2, profile.sport_3 = sports
                profile.save()
                messages.success(request, "Tu actividad se actualizó.")
                return redirect("dashboard")
            if frequency not in dict(AthleteProfile.ACTIVITY_CHOICES):
                messages.error(request, "Selecciona con qué frecuencia haces deporte.")
            elif any(sport and sport not in allowed_sports for sport in sports):
                messages.error(request, "Selecciona deportes de la lista.")
            else:
                messages.error(request, "No selecciones el mismo deporte más de una vez.")

    return render(
        request,
        "edit_profile.html",
        {**_activity_context(profile), "section": section},
    )


def logout_view(request):
    auth_logout(request)
    return redirect("login")
