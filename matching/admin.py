from django.contrib import admin
from .models import MatchResult


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ['match_id', 'report_1', 'report_2', 'similarity_score',
                    'confidence_level', 'match_status', 'detected_at']
    list_filter = ['match_status', 'confidence_level', 'match_type', 'detected_at']
    search_fields = ['report_1__report_code', 'report_2__report_code']
    readonly_fields = ['match_id', 'detected_at']

    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('match_id', 'report_1', 'report_2')
        }),
        ('النتائج', {
            'fields': ('similarity_score', 'confidence_level', 'match_type', 'match_status')
        }),
        ('التفاصيل', {
            'fields': ('match_reason',)
        }),
        ('التواريخ', {
            'fields': ('detected_at',)
        }),
    )