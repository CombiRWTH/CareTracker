"""Run a cronjob at the beginning of each month and calculate the statistics for the previous month."""
import django
django.setup()
from backend.models import (Station, StationWorkloadDaily, StationWorkloadMonthly)  # noqa: E402
from datetime import datetime, timedelta, date  # noqa: E402
from calendar import monthrange  # noqa: E402


def calculate_monthly_station_minutes(station: int, date: date, shift: str) -> dict:
    """Calculate the total minutes assigned for one station for one whole month.

    Args:
        station (int): The station id for which the toal minutes should be calculated
        shift: The shift for which the data is requested
        date (date): The first of the month for which the toal minutes should be claculated

    Returns:
        int: dict
    """
    # Filter the database entries for the correct month, station and shift
    days = StationWorkloadDaily.objects.filter(
        date__month=date.month, date__year=date.year, station=station, shift=shift).values()

    # If no entries where found return
    if not days.exists():
        return -1

    # Add up the minutes of all the filtered days to get a total for the month
    minutes_total = 0
    patients_total = 0
    caregivers_total = 0
    suggested_total = 0
    for entry in days:
        minutes_total += entry['minutes_total'] if entry['minutes_total'] else 0
        patients_total += entry['patients_total'] if entry['patients_total'] else 0
        caregivers_total += entry['caregivers_total'] if entry['caregivers_total'] else 0
        suggested_total += entry['PPBV_suggested_caregivers'] if entry['PPBV_suggested_caregivers'] else 0

    return {"minutes_total": minutes_total, "patients_total": patients_total,
            "caregivers_total": caregivers_total, "suggested_total": suggested_total}


def calculate_total_minutes_per_station(station: int, date: date, shift: str) -> None:
    """Calculate the total minutes assigned for one station for one whole month.

    Args:
        station (int): The station id for which the toal minutes should be calculated
        date (date): The first of the month for which the toal minutes should be claculated
        shift (str): The shift for which the data is requested
    """
    # Compute statistics for the given shift
    dict_res_day = calculate_monthly_station_minutes(station, date, shift)
    if not dict_res_day == -1:
        days_in_month = monthrange(date.year, date.month)[1]
        # Skip if no data was found
        patients_avg = dict_res_day['patients_total'] / days_in_month
        caregivers_avg = dict_res_day['caregivers_total'] / days_in_month

        # According to article 4.2 of the PPBV
        suggested_caregivers_avg = (dict_res_day['minutes_total'] / (38.5 * 60)) / days_in_month

        StationWorkloadMonthly.objects.update_or_create(
            station=station,
            month=date,
            shift=shift,
            defaults=dict(
                patients_avg=patients_avg,
                actual_caregivers_avg=caregivers_avg,
                suggested_caregivers_avg=suggested_caregivers_avg,
                minutes_total=dict_res_day['minutes_total']
            )
        )


def calculate():
    """Calculate the statistics for the previous month for all stations and shifts."""
    date = datetime.today() - timedelta(days=1)  # Get previous month
    stations = Station.objects.all()
    for station in stations:
        calculate_monthly_station_minutes(station.id, date, 'DAY')
        calculate_monthly_station_minutes(station.id, date, 'NIGHT')


if __name__ == '__main__':
    calculate()
