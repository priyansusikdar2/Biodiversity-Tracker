from django.contrib import admin
from django.utils.html import format_html
from .models import Species, Observation, Alert, BiodiversityMetric, UserProfile

@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ['name', 'scientific_name', 'category', 'conservation_status', 'detection_count', 'last_seen']
    list_filter = ['category', 'conservation_status', 'is_native']
    search_fields = ['name', 'scientific_name', 'common_names']
    readonly_fields = ['detection_count', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'scientific_name', 'common_names', 'description')
        }),
        ('Classification', {
            'fields': ('category', 'kingdom', 'phylum', 'class_name', 'order', 'family', 'genus')
        }),
        ('Conservation', {
            'fields': ('conservation_status', 'threat_factors', 'is_native')
        }),
        ('Statistics', {
            'fields': ('detection_count', 'last_seen', 'confidence_threshold'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_endangered', 'export_as_csv']
    
    @admin.action(description='Mark selected as Endangered')
    def mark_as_endangered(self, request, queryset):
        updated = queryset.update(conservation_status='EN')
        self.message_user(request, f'{updated} species marked as Endangered')
    
    @admin.action(description='Export to CSV')
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="species.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Scientific Name', 'Category', 'Status', 'Detection Count'])
        for species in queryset:
            writer.writerow([species.name, species.scientific_name, 
                           species.category, species.conservation_status, 
                           species.detection_count])
        return response

@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ['id', 'species_name', 'observer', 'timestamp', 'location', 'confidence_score', 'image_preview']
    list_filter = ['ai_verified', 'confidence_score', 'timestamp', 'weather_condition']
    search_fields = ['species__name', 'location', 'notes', 'observer__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    def species_name(self, obj):
        return obj.species.name if obj.species else "Unknown"
    species_name.short_description = 'Species'
    species_name.admin_order_field = 'species__name'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 5px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'severity', 'is_resolved', 'created_at', 'resolved_at']
    list_filter = ['alert_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['title', 'message', 'trigger_reason']
    readonly_fields = ['created_at', 'resolved_at']
    
    actions = ['resolve_selected']
    
    @admin.action(description='Resolve selected alerts')
    def resolve_selected(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_resolved=True, resolved_at=timezone.now())
        self.message_user(request, f'{updated} alerts resolved')

@admin.register(BiodiversityMetric)
class BiodiversityMetricAdmin(admin.ModelAdmin):
    list_display = ['date', 'shannon_index', 'simpson_index', 'species_richness', 'total_observations', 'evenness']
    list_filter = ['date']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'organization', 'total_observations', 'join_date', 'is_verified']
    list_filter = ['role', 'is_verified']
    search_fields = ['user__username', 'user__email', 'organization']
    readonly_fields = ['total_observations', 'join_date']