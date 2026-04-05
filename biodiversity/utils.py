import numpy as np
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Observation, BiodiversityMetric, Alert

def calculate_shannon_index(observations):
    """Calculate Shannon-Wiener Diversity Index"""
    if not observations:
        return 0.0
    
    species_counts = {}
    for obs in observations:
        if obs.species_id:
            species_counts[obs.species_id] = species_counts.get(obs.species_id, 0) + 1
    
    total = len(observations)
    shannon = 0
    for count in species_counts.values():
        pi = count / total
        shannon -= pi * np.log(pi)
    
    return round(shannon, 4)

def calculate_simpson_index(observations):
    """Calculate Simpson's Diversity Index"""
    if not observations:
        return 0.0
    
    species_counts = {}
    for obs in observations:
        if obs.species_id:
            species_counts[obs.species_id] = species_counts.get(obs.species_id, 0) + 1
    
    total = len(observations)
    sum_squares = sum(count * (count - 1) for count in species_counts.values())
    
    if total <= 1:
        return 0.0
    
    return round(1 - (sum_squares / (total * (total - 1))), 4)

def calculate_evenness(observations):
    """Calculate Pielou's Evenness"""
    if not observations:
        return 0.0
    
    unique_species = set(obs.species_id for obs in observations if obs.species_id)
    species_count = len(unique_species)
    
    if species_count <= 1:
        return 1.0
    
    shannon = calculate_shannon_index(observations)
    return round(shannon / np.log(species_count), 4)

def calculate_biodiversity_metrics(date=None):
    """Calculate comprehensive biodiversity metrics"""
    if date is None:
        date = timezone.now().date()
    
    start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
    end = start + timedelta(days=1)
    
    observations = Observation.objects.filter(timestamp__gte=start, timestamp__lt=end, species__isnull=False)
    
    species_richness = observations.values('species').distinct().count()
    total_obs = observations.count()
    shannon = calculate_shannon_index(observations)
    simpson = calculate_simpson_index(observations)
    evenness = calculate_evenness(observations)
    
    endangered_count = observations.filter(species__conservation_status__in=['CR', 'EN']).values('species').distinct().count()
    
    metric, created = BiodiversityMetric.objects.get_or_create(
        date=date,
        defaults={
            'shannon_index': shannon,
            'simpson_index': simpson,
            'species_richness': species_richness,
            'evenness': evenness,
            'total_observations': total_obs,
            'endangered_species_count': endangered_count,
        }
    )
    
    if not created:
        metric.shannon_index = shannon
        metric.simpson_index = simpson
        metric.species_richness = species_richness
        metric.evenness = evenness
        metric.total_observations = total_obs
        metric.endangered_species_count = endangered_count
        metric.save()
    
    # Check for alerts
    previous = BiodiversityMetric.objects.filter(date__lt=date).order_by('-date').first()
    if previous and previous.shannon_index > 0:
        decline = ((previous.shannon_index - shannon) / previous.shannon_index) * 100
        if decline > 20:
            Alert.objects.get_or_create(
                alert_type='BD',
                title='Biodiversity Decline Detected',
                defaults={'message': f'Biodiversity index dropped by {decline:.1f}%', 'severity': 'H'}
            )
    
    return metric

def generate_biodiversity_report(start_date, end_date):
    """Generate comprehensive biodiversity report"""
    metrics = BiodiversityMetric.objects.filter(date__range=[start_date, end_date]).order_by('date')
    
    if not metrics.exists():
        return None
    
    return {
        'period': {'start_date': start_date, 'end_date': end_date, 'days': (end_date - start_date).days},
        'averages': {
            'shannon_index': round(metrics.aggregate(Avg('shannon_index'))['shannon_index__avg'] or 0, 4),
            'simpson_index': round(metrics.aggregate(Avg('simpson_index'))['simpson_index__avg'] or 0, 4),
            'species_richness': round(metrics.aggregate(Avg('species_richness'))['species_richness__avg'] or 0, 2),
        },
        'total_observations': metrics.aggregate(Sum('total_observations'))['total_observations__sum'] or 0,
        'metrics_count': metrics.count(),
    }