"""
URL configuration for brokerage_notes app.
"""
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    path('api/brokerage-notes/', csrf_exempt(views.BrokerageNoteListView.as_view()), name='note-list'),
    path('api/brokerage-notes/<str:note_id>/', csrf_exempt(views.BrokerageNoteDetailView.as_view()), name='note-detail'),
    path('api/brokerage-notes/<str:note_id>/operations/', views.BrokerageNoteOperationsView.as_view(), name='note-operations'),
]

