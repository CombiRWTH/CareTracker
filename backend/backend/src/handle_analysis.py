"""This contains endpoints to return analysis data for the frontend."""
from django.http import JsonResponse
from ..models import StationWorkloadDaily, Station
from datetime import datetime, date, timedelta


def get_should_vs_is_analysis(start: date, end: date) -> list:
    """Return the should vs is analysis data for all stations.

    Returns:
        list: The should vs is analysis data for each station.
    """
    stations = Station.objects.all()
    analysis_data = []
    for station in stations:
        workload = StationWorkloadDaily.objects.filter(
            station=station.id,
            date__gte=start,
            date__lte=end,
        ).order_by('-date').values('date', 'caregivers_total', 'PPBV_suggested_caregivers', 'shift')

        # The number of caregivers needed for that shift will be returned
        data = {
            'station_id': station.id,
            'station_name': station.name,
            'dataset_night': [
                {
                    'date': entry['date'],
                    'should': round(
                        entry['PPBV_suggested_caregivers'] * 38.5 / 8, 2
                    ) if entry['PPBV_suggested_caregivers'] else 0,
                    'is': round(entry['caregivers_total'], 2) if entry['caregivers_total'] else 0
                }
                for entry in workload if entry['shift'] == 'NIGHT'
            ],
            'dataset_day': [
                {
                    'date': entry['date'],
                    'should': round(
                        entry['PPBV_suggested_caregivers'] * 38.5 / 8, 2
                    ) if entry['PPBV_suggested_caregivers'] else 0,
                    'is': round(entry['caregivers_total'], 2) if entry['caregivers_total'] else 0
                }
                for entry in workload if entry['shift'] == 'DAY'
            ]
        }
        analysis_data.append(data)

    return analysis_data


def aggregate_analysis_data(start: date, end: date) -> dict:
    """Aggregate the analysis data for each station for a given time period.

    The same format as from the get_should_vs_is_analysis function is returned, so the front end wont need changing.

    Args:
        start (date): The start date for the analysis.
        end (date): The end date for the analysis

    Returns:
        dict: The aggregated analysis data.
    """
    analysis = get_should_vs_is_analysis(start, end)
    for station_data in analysis:
        day_sum_should = round(sum(entry['should'] for entry in station_data['dataset_day']), 2)
        day_sum_is = round(sum(entry['is'] for entry in station_data['dataset_day']), 2)
        night_sum_should = round(sum(entry['should'] for entry in station_data['dataset_night']), 2)
        night_sum_is = round(sum(entry['is'] for entry in station_data['dataset_night']), 2)
        station_data['dataset_day'] = [{'date': 'Total', 'should': day_sum_should, 'is': day_sum_is}]
        station_data['dataset_night'] = [
            {'date': 'Total', 'should': night_sum_should, 'is': night_sum_is}
        ]

    return analysis


def get_station_specific_analysis(station_id: int, start: date, end: date) -> dict:
    """Retrieve data for a specific station.

    Args:
        station_id (int): The id of the station.
        start (date): From where to start.
        end (date): Where to end.

    Returns:
        dict: The data for the specific station.
    """
    analysis_data = next(
        (data for data in get_should_vs_is_analysis(start, end) if data['station_id'] == station_id),
        None
    )
    # Add dates which are not in the database
    for analysis_date in (start + timedelta(n) for n in range(int((end - start).days) + 1)):
        if not any(entry['date'] == analysis_date for entry in analysis_data['dataset_day']):
            analysis_data['dataset_day'].append({'date': analysis_date, 'should': 0, 'is': 0})
        if not any(entry['date'] == analysis_date for entry in analysis_data['dataset_night']):
            analysis_data['dataset_night'].append({'date': analysis_date, 'should': 0, 'is': 0})

    # Sort the data by date
    analysis_data['dataset_day'] = sorted(analysis_data['dataset_day'], key=lambda x: x['date'])
    analysis_data['dataset_night'] = sorted(analysis_data['dataset_night'], key=lambda x: x['date'])
    return analysis_data


def handle_should_vs_is_analysis(request, start: str, end: str) -> JsonResponse:
    """Endpoint to retrieve coordinates for the is and should occupancy on stations.

    Args:
        request (HttpRequest): The request object.
        start (str): The start date for the analysis.
        end (str): The end date for the analysis.

    Returns:
        JsonResponse: The response containing the should vs is analysis data.
    """
    if request.method == 'GET':
        try:
            start = datetime.strptime(start, '%Y-%m-%d').date()
            end = datetime.strptime(end, '%Y-%m-%d').date()
            return JsonResponse(aggregate_analysis_data(start, end), safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD.'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


def handle_station_specific_analysis(request, station_id: int, start: str, end: str) -> JsonResponse:
    """Endpoint to retrieve coordinates for the is and should occupancy on a specific station.

    Args:
        request (HttpRequest): The request object.
        station_id (int): The id of the station.
        start (str): The start date for the analysis.
        end (str): The end date for the analysis.

    Returns:
        JsonResponse: The response containing the should vs is analysis data.
    """
    if request.method == 'GET':
        try:
            start = datetime.strptime(start, '%Y-%m-%d').date()
            end = datetime.strptime(end, '%Y-%m-%d').date()
            return JsonResponse(get_station_specific_analysis(station_id, start, end), safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD.'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
