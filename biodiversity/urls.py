from django.urls import path
from . import views

urlpatterns = [
    # ========== MAIN PAGES ==========
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_image, name='upload'),
    
    # ========== SPECIES URLs ==========
    path('species/', views.species_list, name='species_list'),
    path('species/<int:pk>/', views.species_detail, name='species_detail'),
    
    # ========== OBSERVATION URLs ==========
    path('observation/<int:pk>/', views.observation_detail, name='observation_detail'),
    
    # ========== ALERT URLs ==========
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/resolve/<int:pk>/', views.resolve_alert, name='resolve_alert'),
    
    # ========== REPORTS ==========
    path('report/', views.biodiversity_report, name='biodiversity_report'),
    
    # ========== API ENDPOINTS ==========
    # AI Detection
    path('api/detect-species/', views.api_detect_species, name='api_detect_species'),
    path('api/test-ai/', views.test_ai_detection, name='test_ai_detection'),
    path('api/ai-status/', views.ai_status, name='ai_status'),
    
    # Alert Management APIs
    path('api/resolve-all-alerts/', views.resolve_all_alerts, name='resolve_all_alerts'),
    path('api/create-sample-alert/', views.create_sample_alert, name='create_sample_alert'),
    path('api/alert-details/<int:pk>/', views.alert_details_api, name='alert_details_api'),
    path('api/export-alerts/', views.export_alerts, name='export_alerts'),
    path('api/check-new-alerts/', views.check_new_alerts, name='check_new_alerts'),
    
    # ========== HEALTH CHECK ==========
    path('health/', views.health_check, name='health_check'),
]

# Optional: Custom error handlers (uncomment if you have these views)
# handler404 = views.custom_404
# handler500 = views.custom_500