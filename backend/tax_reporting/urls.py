from django.urls import path
from .views import CapitalGainsReportView

urlpatterns = [
    path(
        'api/tax-reporting/capital-gains/',
        CapitalGainsReportView.as_view(),
        name='capital-gains-report',
    ),
]
