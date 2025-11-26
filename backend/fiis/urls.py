from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    path('api/fiis/profiles/', csrf_exempt(views.FIIProfileListView.as_view()), name='fii-profile-list'),
    path('api/fiis/profiles/<str:ticker>/', csrf_exempt(views.FIIProfileDetailView.as_view()), name='fii-profile-detail'),
]
