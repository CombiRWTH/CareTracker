"""This file contains the URL patterns for the API."""

from django.urls import path

from .src import (
    handle_analysis,
    handle_calculations,
    handle_data_imports,
    handle_patients,
    handle_questions,
    handle_stations,
)

urlpatterns = [
    # Station Endpoints
    path("stations/", handle_stations.handle_stations, name="handle_stations"),
    path(
        "stations/<int:station_id>/",
        handle_patients.handle_patients,
        name="handle_patients",
    ),
    path(
        "stations/analysis",
        handle_stations.handle_stations_analysis,
        name="stations-analysis",
    ),
    path(
        "visit-type/<int:station_id>/",
        handle_patients.handle_visit_type,
        name="handle_visit_type",
    ),
    path(
        "current-station/<int:patient_id>/",
        handle_patients.handle_current_station_of_patient,
        name="handle_current_station_of_patient",
    ),
    # Patient Endpoints
    path(
        "patient/dates/<int:patient_id>/<int:station_id>/",
        handle_patients.handle_patient_dates,
        name="handle_patient_dates",
    ),
    path(
        "classification/<int:station_id>/<int:patient_id>/<str:date>/",
        handle_patients.handle_get_classification,
        name="handle_get_classification",
    ),
    # Calculation Endpoints
    path(
        "calculate/<int:station_id>/<int:patient_id>/<str:date>/",
        handle_calculations.handle_calculations,
        name="handle_calculations",
    ),
    path(
        "calculate_direct/<int:station_id>/<int:patient_id>/<str:date>/<str:a_value>/<str:s_value>/",
        handle_calculations.handle_direct_classification,
        name="handle_direct_calculations",
    ),
    path(
        "questions/<int:station_id>/<int:patient_id>/<str:date>/",
        handle_questions.handle_questions,
        name="handle_questions",
    ),
    # Import Endpoints
    path(
        "import/patient/",
        handle_data_imports.handle_patient_data_import,
        name="handle_patient_data_import",
    ),
    path(
        "import/caregiver/",
        handle_data_imports.handle_caregiver_shift_import,
        name="handle_caregiver_shift_import",
    ),
    # Analysis Endpoints
    path(
        "analysis/caregivers/<str:start>/<str:end>/",
        handle_analysis.handle_should_vs_is_analysis,
        name="handle_should_vs_is_analysis",
    ),
    path(
        "analysis/caregivers/<int:station_id>/<str:start>/<str:end>/",
        handle_analysis.handle_station_specific_analysis,
        name="handle_station_specific_analysis",
    ),
]
