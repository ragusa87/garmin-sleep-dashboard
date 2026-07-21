from django.contrib import admin

from .models import DailySummary, SleepNight


@admin.register(SleepNight)
class SleepNightAdmin(admin.ModelAdmin):
    list_display = ("calendar_date", "score_overall", "deep_s", "rem_s", "lowest_spo2", "source")
    list_filter = ("source",)
    date_hierarchy = "calendar_date"


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ("calendar_date", "steps", "resting_hr", "avg_stress", "source")
    list_filter = ("source",)
    date_hierarchy = "calendar_date"
