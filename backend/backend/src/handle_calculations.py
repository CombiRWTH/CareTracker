"""Calculate the minutes each patient should receive care services."""
from datetime import date, datetime

from django.http import JsonResponse
from django.utils import timezone

from ..models import DailyClassification, DailyPatientData, Patient, Station
from .handle_questions import get_questions
from cronjobs.src.daily_calculation_cronjob import calculate_minutes_per_station
from cronjobs.src.monthly_calc_cronjob import calculate_total_minutes_per_station


def recompute_station_data(station_id: int, date: date) -> None:
    """In case of a change in the patient's data, the daily/monthly data has to be recomputed.

    Additionally once all patients are classified for the day, the daily data has to be recomputed.
    Same goes for the monthly data.

    Args:
        station_id (int): The ID of the station.
        date (date): The date of the classification.
    """
    date = datetime.strptime(date, "%Y-%m-%d").date()
    station = Station.objects.get(id=station_id)

    # Recompute the daily data
    calculate_minutes_per_station(station, date)

    # Recompute the monthly data
    calculate_total_minutes_per_station(station, date, 'DAY')


def group_and_count_data(data: list) -> dict:
    """Group the data count the number of entries in each group.

    The data is grouped by care_service_category, care_service_range and care_service_task.
    The count of each group is also tracked.

    Args:
        data (list): The data to group and count.

    Returns:
        dict: The grouped and counted data.
    """
    data_groups = {'A': {}, 'S': {}, 'A_Value': 0, 'S_Value': 0}
    for entry in data:
        category = entry['field__short']
        range = entry['severity']
        task = entry['category__name']

        # Add keys if not already in data_groups
        if range not in data_groups[category]:
            data_groups[category][range] = {}
        if task not in data_groups[category][range]:
            data_groups[category][range][task] = 0

        # Add the entry to the data_groups
        data_groups[category][range][task] += 1
    return data_groups


def choose_general_care_group(data: dict, barthel_index: int, expanded_barthel_index: int, mini_mental_status: int) \
        -> int:
    """According to the PPBV, the patient is assigned to a care group based on the provided data.

    A patient belongs to one of the following care groups if the statement is true:
    1. A1, if no other category
    2. A2, if at least 1 performance characteristic (from level A2) applies in at least 2 areas OR at least 1 from A2
       and max. 1 from A3
    3. A3, if at least 2 areas have at least 1 performance characteristic from A3
    4. A4, if at least 2 areas A4 and at least 1 of the following applies:
      - the patient has a Barthel Index between 0 and 35 points,
      - the patient has an extended Barthel Index between 0 and 15 points, or
      - the patient has scored between 0 and 16 points in the Mini-Mental Status Test.

    Args:
        data (dict): The data grouped by care_service_category and care_service_range.
        barthel_index (int): The barthel index of the patient.
        expanded_barthel_index (int): The expanded barthel index of the patient.
        mini_mental_status (int): The mini mental status of the patient.

    Returns:
        int: The care group the patient belongs to.
    """
    if ((4 in data and len(data[4]) > 1)
            and (barthel_index <= 35 or expanded_barthel_index <= 15 or mini_mental_status <= 16)):
        # Patient is in the highest care category
        return 4
    elif 3 in data and len(data[3]) > 1:
        # Patient is in the third care category
        return 3
    elif 2 in data and (len(data[2]) > 1 or (3 in data and len(data[3]) > 0)):
        # Patient is in the second care category
        return 2
    else:
        # Patient is in the first care category
        return 1


def choose_specific_care_group(data: dict) -> int:
    """According to the PPBV, the patient is assigned to a care group based on the provided data.

    A patient belongs to one of the following care groups if the statement is true:
    1. S1, if no other
    2. S2, if at least 1 allocation characteristic from S2
    3. S3, if at least 1 allocation characteristic from S3 applies
    4. S4, if at least 1 allocation characteristic from S3 applies in at least 2 areas

    Args:
        data (dict): The data grouped by care_service_category and care_service_range.

    Returns:
        int: The care group the patient belongs to.
    """
    if 3 in data and len(data[3]) > 1:
        # Patient is in the highest care category
        return 4
    elif 3 in data:
        # Patient is in the third care category
        return 3
    elif 2 in data:
        # Patient is in the second care category
        return 2
    else:
        # Patient is in the first care category
        return 1


def has_entry_for_current_quarter(patient_id: int, date: str) -> bool:
    """Check if there is already an entry for the current quarter.

    Returns:
        bool: True if there is already an entry for the current quarter, False otherwise.
    """
    # Find the current quarter
    q_1 = (1, 2, 3)
    q_2 = (4, 5, 6)
    q_3 = (7, 8, 9)
    q_4 = (10, 11, 12)
    date = datetime.strptime(date, "%Y-%m-%d").date()
    if date.month in q_1:
        quarter = q_1
    elif date.month in q_2:
        quarter = q_2
    elif date.month in q_3:
        quarter = q_3
    else:
        quarter = q_4

    # Check if there is already an entry for the current quarter of this year
    entry = DailyPatientData.objects.filter(
        patient=patient_id,
        date__year=date.year,
        date__month__in=quarter,
        uses_quarter_entry=True
    ).first()
    return entry is not None


def sum_minutes(a_value: str, s_value: str, body: dict) -> int:
    """Sum up the minutes of the provided data.

    Args:
        a_value (str): The severity of the A group.
        s_value (str): The severity of the S group.
        body (dict): Additional data influencing the minutes.

    Returns:
        int: The sum of the minutes.
    """
    # In case of a day of discharge, half the minutes_per_classification of the previous day are used (§ 12 (2)).
    # TODO: Issue
    minutes = 33  # Base value (§ 4 (2) 1. and  § 12 Absatz 1 Satz 1)
    if body.get("is_in_isolation", False):
        minutes = 123  # Base value for isolation (§ 4 (2) 2. and § 12 Absatz 1 Satz 2)

    # Data taken from the PPBV (§ 12 Absatz 4 Satz 1)
    minutes_per_classification = {
        "A1": {
            "S1": 59,
            "S2": 76,
            "S3": 112,
            "S4": 151
        },
        "A2": {
            "S1": 114,
            "S2": 131,
            "S3": 167,
            "S4": 206
        },
        "A3": {
            "S1": 203,
            "S2": 220,
            "S3": 256,
            "S4": 295
        },
        "A4": {
            "S1": 335,
            "S2": 352,
            "S3": 388,
            "S4": 427
        }
    }
    minutes += minutes_per_classification[f'A{a_value}'][f'S{s_value}']

    if body.get("is_semi_stationary", False):
        minutes /= 2  # Only use half of the minutes (§ 4 (2) 3.)

    # § 4 (2) 3. and § 12 Absatz 3
    if body.get("is_fully_stationary", False) and body.get(
        "is_day_of_admission", False
    ):
        minutes += 75
    if body.get("is_semi_stationary", False) and not body.get(
        "is_repeating_visit", False
    ):
        minutes += 75

    # Repeating visits due to same illness lead to less minutes for admission (§ 4 (2) 4. Satz 2)
    if (
        body.get("is_semi_stationary", False)
        and body.get("is_repeating_visit", False)
        and not body.get("has_entry_for_current_quarter", False)
    ):
        minutes += 75

    return minutes


def calculate_care_minutes(body_data: dict) -> int:
    """Calculate the minutes each patient should receive care services for.

    The body_data should contain the following:
    - selected_care_services: A list of care services the patient should receive
      (same format as provided by the handle_questions endpoint).
    - barthel_index: The barthel index of the patient.
    - expanded_barthel_index: The expanded barthel index of the patient.
    - mini_mental_status: The mini mental status of the patient.

    Args:
        body_data (dict): The data to calculate the minutes from.

    Returns:
        int: The minutes the patient should receive care services.
        int: The severity of the general care group.
        int: The severity of the specific care group.
    """
    # Sort data to iterate over it
    data_groups = group_and_count_data(body_data['care_service_options'])

    # Calculate service category's severity
    a_index = choose_general_care_group(
        data_groups['A'],
        body_data['barthel_index'],
        body_data['expanded_barthel_index'],
        body_data['mini_mental_status']
    )
    s_index = choose_specific_care_group(data_groups['S'])

    # Calculate the minutes accordingly
    return sum_minutes(a_index, s_index, body_data), a_index, s_index


def calculate_result(station_id: int, patient_id: int, date: date) -> dict:
    """Calculate the minutes a caregiver has time for caring for a patient.

    Args:
        station_id (int): The ID of the station.
        patient_id (int): The ID of the patient.
        date (date): The date of the classification.

    Returns:
        dict: The response containing the calculated minutes, the general and the specific care group.
    """
    patient = Patient.objects.get(id=patient_id)
    station = Station.objects.get(id=station_id)

    # Find the classification of the patient for the specified date
    classification = DailyClassification.objects.filter(
        patient=patient,
        station=station,
        date=date,
    ).first()

    if classification is None:
        return {'error': 'No classification found for the specified date.'}

    # Get all selected care services
    entries = get_questions(station_id, patient_id, date)
    entries['care_service_options'] = [
        option for option in entries['care_service_options']
        if option['selected']
    ]

    # Add more data provided by the hospital
    patient_data = DailyPatientData.objects.filter(
        patient=patient,
        station=station,
        date=date,
    ).values().first()
    entries.update(patient_data)

    datetime_date = datetime.strptime(date, "%Y-%m-%d").date()
    entries['is_day_of_admission'] = datetime_date == timezone.localtime(patient_data['day_of_admission']).date()
    entries['is_day_of_discharge'] = datetime_date == timezone.localtime(patient_data['day_of_discharge']).date()

    if not entries['uses_quarter_entry']:
        entries['has_entry_for_current_quarter'] = has_entry_for_current_quarter(patient_id, date)
        if (entries['is_semi_stationary']
                and entries['is_repeating_visit']
                and not entries['has_entry_for_current_quarter']):
            # The extra minutes will be used for the repeating visit
            patient_data['is_repeating_visit'] = True
    else:
        # Use the quarter entry again for the calculation since it is already used for the patient on this day
        entries['has_entry_for_current_quarter'] = False

    # Calculate the minutes accordingly
    minutes_to_take_care, a_index, s_index = calculate_care_minutes(entries)

    # Update the classification with the new minutes
    classification.result_minutes = minutes_to_take_care
    classification.a_index = a_index
    classification.s_index = s_index
    classification.save()

    # Check for possible recomputation of daily and monthly data
    recompute_station_data(station_id, date)

    return {'minutes': minutes_to_take_care, 'category1': a_index, 'category2': s_index}


def calculate_direct_classification(
    station_id: int, patient_id: int, date: date, a_value: str, s_value: str
):
    """Calculate care minutes based on a_value and s_value alone.

     Args:
        station_id (int): The ID of the station.
        patient_id (int): The ID of the patient.
        date (date): The date of the classification.
        a_value (str): The severity of the A group.
        s_value (str): The severity of the S group.

    Returns:
        dict: The response containing the calculated minutes, the general and the specific care group.
    """
    patient = Patient.objects.get(id=patient_id)
    station = Station.objects.get(id=station_id)

    # Create "default" dailyClassification if it does not exist
    classification = DailyClassification.objects.filter(
        patient=patient,
        station=station,
        date=date,
    ).first()

    if classification is None:
        classification = DailyClassification.objects.create(
            patient=patient,
            date=date,
            is_in_isolation=False,
            result_minutes=0,
            a_index=0,
            s_index=0,
            station=station,
        )

    # If there is dailyPatientData, store information that influences the care minutes
    direct_classification_data = {}

    patient_data = (
        DailyPatientData.objects.filter(
            patient=patient,
            station=station,
            date=date,
        )
        .values()
        .first()
    )

    if patient_data is not None:
        direct_classification_data.update(patient_data)

        datetime_date = datetime.strptime(date, "%Y-%m-%d").date()
        direct_classification_data["is_day_of_admission"] = (
            datetime_date == timezone.localtime(patient_data["day_of_admission"]).date()
        )
        direct_classification_data["is_day_of_discharge"] = (
            datetime_date == timezone.localtime(patient_data["day_of_discharge"]).date()
        )

        if not direct_classification_data["uses_quarter_entry"]:
            direct_classification_data["has_entry_for_current_quarter"] = (
                has_entry_for_current_quarter(patient_id, date)
            )
            if (
                direct_classification_data["is_semi_stationary"]
                and direct_classification_data["is_repeating_visit"]
                and not direct_classification_data["has_entry_for_current_quarter"]
            ):
                # The extra minutes will be used for the repeating visit
                patient_data["is_repeating_visit"] = True
        else:
            # Use the quarter entry again for the calculation since it is already used for the patient on this day
            direct_classification_data["has_entry_for_current_quarter"] = False

    # Calculate the minutes accordingly
    minutes_to_take_care = sum_minutes(a_value, s_value, direct_classification_data)

    # Update dailyClassification
    classification.result_minutes = minutes_to_take_care
    classification.a_index = a_value
    classification.s_index = s_value
    classification.save()

    # Check for possible recomputation of daily and monthly data
    recompute_station_data(station_id, date)

    return {"minutes": minutes_to_take_care, "category1": a_value, "category2": s_value}


def handle_calculations(request, station_id, patient_id: int, date: date):
    """Endpoint to calculate the minutes a caregiver has time for caring for a patient.

    Args:
        request (HttpRequest): The request object.
        station_id (int): The ID of the station.
        patient_id (int): The ID of the patient.
        date (str): The date of the classification ('YYYY-MM-DD').

    Returns:
        JsonResponse: The response containing the calculated minutes.
    """
    if request.method == 'GET':
        return JsonResponse(calculate_result(station_id, patient_id, date), status=200)
    else:
        return JsonResponse({'message': 'Method not allowed.'}, status=405)


def handle_direct_classification(
    request,
    station_id: int,
    patient_id: int,
    date: date,
    a_value: str,
    s_value: str,
):
    """Endpoint to directly classify a patient.

    Args:
        request (HttpRequest): The request object.
        station_id (int): The ID of the station.
        patient_id (int): The ID of the patient.
        date (str): The date of the classification ('YYYY-MM-DD').
        a_value (str): The severity of the A group.
        s_value (str): The severity of the S group.

    Returns:
        JsonResponse: The response containing the calculated minutes.
    """
    if request.method == "POST":
        return JsonResponse(
            calculate_direct_classification(
                station_id, patient_id, date, a_value, s_value
            ),
            status=200,
        )
    else:
        return JsonResponse({"message": "Method not allowed."}, status=405)
