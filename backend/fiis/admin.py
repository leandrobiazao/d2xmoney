from django.contrib import admin
from .models import FIIProfile

@admin.register(FIIProfile)
class FIIProfileAdmin(admin.ModelAdmin):
    list_display = ['stock', 'segment', 'dividend_yield', 'price_to_vp']
    search_fields = ['stock__ticker', 'segment']
    list_filter = ['segment']
