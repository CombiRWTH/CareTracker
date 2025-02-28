"""Provide an endpoint to retrieve all current patients for a station."""
from datetime import date, timedelta

from django.db.models import F, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.utils import timezone

from ..models import DailyClassification, DailyPatientData, Patient


def get_active_patients_on_station(station_id: int, date: date = date.today()) -> QuerySet[Patient]:
    """Get all patients assigned to a specific station on the given date.

    Args:
        station_id (int): The ID of the station in the database.
        date (date, optional): The date for which to retrieve the patients, defaults to today's date.

    Returns:
        list: The patients assigned to the station.
    """
    patients = DailyPatientData.objects.filter(
        station=station_id,
        date=date
    ).values('patient')

    patients = Patient.objects.filter(id__in=patients)

    return patients


def get_patients_with_additional_information(station_id: int) -> list:
    """Get all patients assigned to a station.

    Additional information is added to each patient:
    - The patient's full name
    - The bed number the patient is currently in
    - The room name the patient is currently in
    - The relevant classification information of the patient for today
    - The relevant classification information of the patient for the previous day
    - The missing classifications for the patient in the last week

    Args:
        station_id (int): The ID of the station.

    Returns:
        list: The patients assigned to the station.
    """
    today = timezone.now().date()

    # Get all patients assigned to the given station
    patients = get_active_patients_on_station(station_id)

    # Add the date the patient was last classified on that station
    patients = patients.annotate(
        lastClassificationDate=Subquery(
            DailyClassification.objects.filter(
                patient=OuterRef("id"), date__lte=today, station=station_id
            )
            .order_by("-date")
            .values("date")[:1]
        ),
        lastClassificationMinutes=Subquery(
            DailyClassification.objects.filter(
                patient=OuterRef("id"), date__lte=today, station=station_id
            )
            .order_by("-date")
            .values("result_minutes")[:1]
        ),
        lastClassificationAIndex=Subquery(
            DailyClassification.objects.filter(
                patient=OuterRef("id"), date__lte=today, station=station_id
            )
            .order_by("-date")
            .values("a_index")[:1]
        ),
        lastClassificationSIndex=Subquery(
            DailyClassification.objects.filter(
                patient=OuterRef("id"), date__lte=today, station=station_id
            )
            .order_by("-date")
            .values("s_index")[:1]
        ),
        currentRoom=Subquery(
            DailyPatientData.objects.filter(
                patient=OuterRef("id"), date=today, station=station_id
            )
            .values("room_name")[:1]
        ),
        currentBed=Subquery(
            DailyPatientData.objects.filter(
                patient=OuterRef("id"), date=today, station=station_id
            )
            .values("bed_number")[:1]
        ),
    ).values(
        "id",
        "name",
        "lastClassificationDate",
        "lastClassificationMinutes",
        "lastClassificationAIndex",
        "lastClassificationSIndex",
        "currentRoom",
        "currentBed",
        name=Concat(F("first_name"), Value(" "), F("last_name"))
    )

    # Convert the QuerySet to a list of dictionaries
    patients_list = list(patients)

    # Add missing classifications for the last week to each patient
    for patient in patients_list:
        patient_id = patient["id"]
        missing_classifications = get_missing_classifications_for_patient(
            patient_id, station_id
        )
        patient["missing_classifications_last_week"] = missing_classifications

    return list(patients)


def get_current_station_for_patient(patient_id: int) -> str:
    """Get the current station for a patient.

    Args:
        patient_id (int): The ID of the patient.

    Returns:
        int: The ID of the station the patient is currently assigned to.
    """
    today = timezone.now().date()
    station = DailyPatientData.objects.filter(
        patient=patient_id,
        date__lte=today
    ).order_by('-date').values('station')[:1]

    return station[0]['station'] if station else None


def get_patient_count_per_station(station_id: int) -> int:
    """Get the number of patients currently assigned to a station. Needed for night shift calculation.

    Args:
        station_id (int): The ID of the station.

    Returns:
        int: The number of patients assigned to the station.
    """
    return get_active_patients_on_station(station_id).count()


def get_patients_visit_type(station_id: int) -> dict:
    """Return lists of patients for a single station classified by visit type.

    Args:
        station_id (int): The ID of the station.

    Returns:
        dict: A dictionary with lists of patients classified by visit type.
    """
    all_patients = get_active_patients_on_station(station_id)
    stationary = (
        []
    )  # normally >= 1 day shift and >= 1 night shift, but here > 24 hours for simplicity
    part_stationary = []  # (6 <= hours < 24) OR (overnight stay AND < 24 hours)
    acute = []  # < 6 hours, only day shift
    undefined = []  # catch possible edges cases

    for patient in all_patients:
        # Get the daily patient data for the patient
        daily_data = DailyPatientData.objects.filter(
            patient=patient, date=timezone.now().date()
        ).first()

        includes_night_time = daily_data.night_stay
        patient_name = f"{patient.first_name} {patient.last_name}"
        stay_duration = daily_data.day_of_discharge - daily_data.day_of_admission

        if stay_duration <= timedelta(hours=6):
            acute.append(patient_name)
        elif (timedelta(hours=6) < stay_duration < timedelta(hours=24)
              or (includes_night_time and stay_duration < timedelta(hours=24))):
            part_stationary.append(patient_name)
        elif stay_duration >= timedelta(hours=24):
            stationary.append(patient_name)
        else:
            undefined.append(patient_name)

    return {
        'stationary': stationary,
        'part_stationary': part_stationary,
        'acute': acute,
        'undefined': undefined
    }


def get_dates_for_patient_classification(patient_id: int, station_id: int) -> list:
    """Get the dates a patient needs a classification, along with the classification status.

    Args:
        patient_id (int): The ID of the patient.
        station_id (int): The ID of the station.

    Returns:
        list: A list of dictionaries containing dates and classification status.
    """
    dates = DailyPatientData.objects.filter(
        patient=patient_id,
        station=station_id,
    ).values_list('date', flat=True)

    result = []

    for date_value in dates:
        has_classification = DailyClassification.objects.filter(
            patient=patient_id,
            station=station_id,
            date=date_value
        ).exists()

        result.append({
            "date": date_value,
            "hasClassification": has_classification
        })

    return result


def get_missing_classifications_for_patient(patient_id: int, station_id: int) -> int:
    """Get the number of missing classifications for a patient in the last week.

    Args:
        patient_id (int): The ID of the patient.
        station_id (int): The ID of the station.

    Returns:
        int: The number of missing classifications for the patient in the last week.
    """
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)

    all_required_days = get_dates_for_patient_classification(patient_id, station_id)
    required_in_last_week = []

    for classification_date in all_required_days:
        if seven_days_ago <= classification_date["date"] <= today:
            required_in_last_week.append(classification_date["date"])

    missing_classifications = []

    for classification_date in required_in_last_week:
        classification = DailyClassification.objects.filter(
            patient=patient_id, date=classification_date, station=station_id
        ).first()

        if classification is None:
            missing_classifications.append(classification_date)

    return missing_classifications


def get_classification_for_patient(
    patient_id: int, station_id: int, date: date
) -> dict:
    """Get the classification of a patient for a specific date.

    Args:
        patient_id (int): The ID of the patient.
        station_id (int): The ID of the station.
        date (date): The date of the classification.

    Returns:
        dict: The classification of the patient.
    """
    classification = DailyClassification.objects.filter(
        patient=patient_id, station=station_id, date=date
    ).first()

    if classification is None:
        return {"error": "No classification found for the specified date."}

    return {
        "a_value": classification.a_index,
        "s_value": classification.s_index,
        "minutes": classification.result_minutes,
    }


def handle_patients(request, station_id: int) -> JsonResponse:
    """Endpoint to retrieve all current patients for a station.

    Args:
        request (HttpRequest): The request object.
        station_id (int): The ID of the station in the database.

    Returns:
        JsonResponse: The response containing the calculated minutes.
    """
    if request.method == 'GET':
        patients = get_patients_with_additional_information(station_id)
        for patient in patients:
            if patient.get("lastClassificationDate"):
                patient["lastClassification"] = {
                    "date": patient.pop("lastClassificationDate"),
                    "minutes": patient.pop("lastClassificationMinutes"),
                    "a_index": patient.pop("lastClassificationAIndex"),
                    "s_index": patient.pop("lastClassificationSIndex"),
                }
            else:
                patient["lastClassification"] = None

        return JsonResponse(patients, safe=False)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


def handle_visit_type(request, station_id: int) -> JsonResponse:
    """Endpoint to retrieve lists of patients for a single station classified by visit type.

    Args:
        request (HttpRequest): The request object.
        station_id (int): The ID of the station in the database.

    Returns:
        JsonResponse: The response containing the patients at station categorized by visit type.
    """
    if request.method == 'GET':
        return JsonResponse(get_patients_visit_type(station_id), safe=False)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


def handle_current_station_of_patient(request, patient_id: int) -> JsonResponse:
    """Endpoint to retrieve the current station of a patient.

    Args:
        request (HttpRequest): The request object.
        patient_id (int): The ID of the patient in the database.

    Returns:
        JsonResponse: The response containing the current station of the patient.
    """
    if request.method == 'GET':
        return JsonResponse({'station_id': get_current_station_for_patient(patient_id)})
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


def handle_patient_dates(request, patient_id: int, station_id: int) -> JsonResponse:
    """Endpoint to retrieve the dates a patient needs a classification.

    This includes dates with and without already made classifications.

    Args:
        request (HttpRequest): The request object.
        patient_id (int): The ID of the patient.
        station_id (int): The ID of the station.

    Returns:
        JsonResponse: The response containing the dates the patient needs a classification.
    """
    if request.method == 'GET':
        return JsonResponse({'dates': get_dates_for_patient_classification(patient_id, station_id)})
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


def handle_get_classification(request, station_id: int, patient_id: int, date: date):
    """Endpoint to get the classification of a patient.

    Args:
        request (HttpRequest): The request object.
        station_id (int): The ID of the station.
        patient_id (int): The ID of the patient.
        date (str): The date of the classification ('YYYY-MM-DD').

    Returns:
        JsonResponse: The response containing the classification.
    """
    if request.method == "GET":
        return JsonResponse(
            get_classification_for_patient(patient_id, station_id, date)
        )
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)
