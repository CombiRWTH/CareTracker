"""Provide the endpoints for handling data imports."""

from io import BytesIO
from django.http import JsonResponse
import pandas as pd
from ..models import Patient, DailyPatientData, Station, StationWorkloadMonthly, StationWorkloadDaily
from datetime import datetime, date, timedelta
from django.utils import timezone


def is_night_stay(date: date, admission_date: datetime, discharge_date: datetime) -> bool:
    """Check if the patient's stay includes time in night shift.

    Args:
        date (date): The date to calculate this for.
        admission_date (datetime): The datetime of the patient's admission.
        discharge_date (datetime): The datetime of the patient's discharge.

    Returns:
        bool: True if the patient stayed overnight, False otherwise.
    """
    night_start = timezone.make_aware(datetime.combine(date, datetime.min.time()) + timedelta(hours=22))
    night_end = timezone.make_aware(datetime.combine(date, datetime.min.time()) + timedelta(hours=6))
    admission_date = timezone.make_aware(admission_date)
    discharge_date = timezone.make_aware(discharge_date)
    if ((admission_date <= night_start <= discharge_date)
            or (admission_date >= night_start and discharge_date <= night_end)):
        return True
    return False


def is_day_stay(date: date, admission_date: datetime, discharge_date: datetime) -> bool:
    """Check if the patient's stay includes time in day shift.

    Args:
        date (date): The date to calculate this for.
        admission_date (datetime): The datetime of the patient's admission.
        discharge_date (datetime): The datetime of the patient's discharge.

    Returns:
        bool: True if the patient stayed during the day, False otherwise.
    """
    day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()) + timedelta(hours=6))
    day_end = timezone.make_aware(datetime.combine(date, datetime.min.time()) + timedelta(hours=22))
    admission_date = timezone.make_aware(admission_date)
    discharge_date = timezone.make_aware(discharge_date)
    if ((admission_date <= day_start <= discharge_date)
            or (admission_date >= day_start and discharge_date <= day_end)):
        return True
    return False


def insert_patient_excel_into_db(df: pd.DataFrame) -> None:
    """Insert patient data from an excel file into the database.

    Args:
        df (DataFrame): The DataFrame containing the patient data.
    """
    for _, row in df.iterrows():
        # Create missing patients
        first_name = row['Vorname']
        last_name = row['Nachname']
        patient_id = row['Patienten-ID']
        date = row['Datum'].date()
        # Check if patient already exists
        if not Patient.objects.filter(id=patient_id).exists():
            Patient.objects.create(
                id=patient_id,
                first_name=first_name,
                last_name=last_name
            )

        # Add daily data
        DailyPatientData.objects.update_or_create(
            patient=Patient.objects.get(id=patient_id),
            station=Station.objects.get(name=row['Stationsname']),
            date=date,
            defaults={
                'is_semi_stationary': row['Teilstationär'] == 'Ja',
                'is_fully_stationary': row['Vollstationär'] == 'Ja',
                'day_of_admission': timezone.make_aware(row['Aufnahmetag']),
                'day_of_discharge': timezone.make_aware(row['Entlassungstag']),
                'is_repeating_visit': row['Wiederkehrend'] == 'Ja',
                'night_stay': is_night_stay(date, row['Aufnahmetag'], row['Entlassungstag']),
                'day_stay': is_day_stay(date, row['Aufnahmetag'], row['Entlassungstag']),
                'room_name': row['Zimmer'],
                'bed_number': row['Bett'],
                'barthel_index': row['Barthel-Index'],
                'expanded_barthel_index': row['Erweiterter Barthel-Index'],
                'mini_mental_status': row['Mini-Mental-Status-Test']
            }
        )


def get_month_number(month: str) -> int:
    """Get the number of the month from its name.

    Args:
        month (str): The name of the month.

    Returns:
        int: The number of the month.
    """
    matchings = {
        'Januar': 1,
        'Februar': 2,
        'März': 3,
        'April': 4,
        'Mai': 5,
        'Juni': 6,
        'Juli': 7,
        'August': 8,
        'September': 9,
        'Oktober': 10,
        'November': 11,
        'Dezember': 12
    }
    return matchings[month]


def add_monthly_data(row: pd.Series) -> None:
    """Add the monthly data to the database.

    Args:
        row (Series): The row containing the data.
    """
    station = Station.objects.get(name=f'Station {str(row["Station"]).strip()}')
    date = datetime.strptime(f"{get_month_number(row['Monat'])} {timezone.now().year}", "%m %Y").date()
    shift = 'DAY' if ('Tag' == row['Schicht']) else 'NIGHT'
    average_caregiver = float(
        row['Durchschnittliche\nPflegepersonalausstattung\nPflegefachkräfte'].replace(',', '.'))
    average_caregiver_helper = float(
        row['Durchschnittliche\nPflegepersonalausstattung\nPflegehilfskräfte'].replace(',', '.'))
    average_midwife = float(row['Durchschnittliche\nPflegepersonalausstattung\nHebammen'].replace(',', '.'))
    average_total = average_caregiver + average_caregiver_helper + average_midwife
    average_patient = float(row['Durchschnittliche\nPatientenbelegung'].replace(',', '.'))

    # Insert data into monthly table
    StationWorkloadMonthly.objects.update_or_create(
        station=station,
        month=date,
        shift=shift,
        defaults={
            'actual_caregivers_avg': average_total,
            'patients_avg': average_patient
        }
    )


def add_daily_data(row: pd.Series) -> None:
    """Add the daily data to the database.

    Args:
        row (Series): The row containing the data.
    """
    station = Station.objects.get(name=f'Station {str(row["Station"]).strip()}')
    date = row['Datum'].date()
    shift = 'DAY' if ('Tag' == row['Schicht']) else 'NIGHT'
    total_caregiver = float(row['Summe\nPflegefachkräfte'].replace(',', '.'))
    total_caregiver_helper = float(row['Summe\nPflegehilfskräfte'].replace(',', '.'))
    total_midwife = float(row['Summe\nHebammen'].replace(',', '.'))
    total_caregivers = total_caregiver + total_caregiver_helper + total_midwife
    total_patient = float(row['Summe\nPatientenbelegung'].replace(',', '.'))

    # Insert data into daily table
    StationWorkloadDaily.objects.update_or_create(
        station=station,
        date=date,
        shift=shift,
        defaults={
            'caregivers_total': total_caregivers,
            'patients_total': total_patient
        }
    )


def insert_caregiver_shift_excel_into_db(df: pd.DataFrame) -> None:
    """Insert caregiver shift data from an excel file into the database.

    Args:
        df (DataFrame): The DataFrame containing the caregiver shift data.
    """
    for _, row in df.iterrows():
        if 'Monat' in row.keys():
            add_monthly_data(row)
        else:
            add_daily_data(row)


def handle_patient_data_import(request) -> JsonResponse:
    """Endpoint to import patient data.

    The body of the request should contain the excel file to be imported.

    Args:
        request (HttpRequest): The request object.

    Returns:
        JsonResponse: The response containing the success message.
    """
    if request.method == 'POST':
        try:
            file = BytesIO(request.body)
            df = pd.read_excel(file, engine='openpyxl')
            insert_patient_excel_into_db(df)
            return JsonResponse({'message': 'File processed successfully'})
        except Exception as e:
            print('Error', e)
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


def handle_caregiver_shift_import(request) -> JsonResponse:
    """Endpoint to import the actual occupancy of caregivers for each station.

    The body of the request should contain the excel file to be imported.
    This can either be a daily (using a date) or montly (using a month) import.

    Args:
        request (HttpRequest): The request object.

    Returns:
        JsonResponse: The response containing the success message.
    """
    if request.method == 'POST':
        try:
            file = BytesIO(request.body)
            df = pd.read_excel(file, engine='openpyxl')
            insert_caregiver_shift_excel_into_db(df)
            return JsonResponse({'message': 'File processed successfully'})
        except Exception as e:
            print('Error', e)
            return JsonResponse({'error': str(e)}, status=400)
