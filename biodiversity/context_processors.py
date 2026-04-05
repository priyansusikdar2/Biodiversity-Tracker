from .models import Alert

def biodiversity_stats(request):
    """Context processor for global biodiversity stats"""
    return {
        'total_alerts_count': Alert.objects.filter(is_resolved=False).count(),
        'unread_alerts_count': Alert.objects.filter(is_resolved=False).count() if request.user.is_authenticated else 0,
    }