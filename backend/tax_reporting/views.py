"""
REST views for tax reporting (IRPF capital gains).
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import CapitalGainsService


class CapitalGainsReportView(APIView):
    """Monthly capital gains report for ações à vista."""

    def get(self, request):
        user_id = request.query_params.get('user_id')
        year_param = request.query_params.get('year', '2025')

        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year_param)
        except ValueError:
            return Response(
                {'error': 'year must be an integer'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report = CapitalGainsService.compute_capital_gains_report(user_id, year)
            return Response(report, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Failed to compute capital gains report', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
