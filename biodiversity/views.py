from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum, Avg, Min, Max
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json
import csv
import logging
import traceback

from .models import Species, Observation, Alert, BiodiversityMetric, UserProfile
from .forms import ObservationUploadForm, SpeciesFilterForm, DateRangeForm
from .ai_model import detect_species_from_image, get_model_info, initialize_model
from .utils import calculate_biodiversity_metrics, generate_biodiversity_report

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main dashboard view"""
    try:
        today = timezone.now().date()
        
        # Statistics
        total_species = Species.objects.count()
        total_observations = Observation.objects.count()
        
        # Today's stats
        today_start = datetime.combine(today, datetime.min.time())
        today_start = timezone.make_aware(today_start)
        today_end = today_start + timedelta(days=1)
        today_observations = Observation.objects.filter(timestamp__gte=today_start, timestamp__lt=today_end).count()
        new_species_today = Species.objects.filter(last_seen__gte=today_start, last_seen__lt=today_end).count()
        
        # Metrics
        latest_metrics = BiodiversityMetric.objects.order_by('-date').first()
        if not latest_metrics and total_observations > 0:
            latest_metrics = calculate_biodiversity_metrics(today)
        
        # Alerts
        active_alerts = Alert.objects.filter(is_resolved=False).order_by('-severity', '-created_at')[:5]
        active_alerts_count = Alert.objects.filter(is_resolved=False).count()
        
        # Recent observations
        recent_observations = Observation.objects.select_related('species', 'observer').order_by('-timestamp')[:10]
        
        # Top species
        top_species = Species.objects.filter(detection_count__gt=0).order_by('-detection_count')[:8]
        max_obs = top_species.first().detection_count if top_species.exists() else 1
        
        # Chart data - Last 7 days
        trend_labels = []
        trend_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            trend_labels.append(date.strftime('%b %d'))
            day_start = datetime.combine(date, datetime.min.time())
            day_start = timezone.make_aware(day_start)
            day_end = day_start + timedelta(days=1)
            count = Observation.objects.filter(
                timestamp__gte=day_start, 
                timestamp__lt=day_end, 
                species__isnull=False
            ).values('species').distinct().count()
            trend_data.append(count)
        
        # Species distribution
        distribution = Species.objects.values('category').annotate(count=Count('id'))
        category_map = {'FA': 'Fauna', 'FL': 'Flora', 'FU': 'Fungi', 'LI': 'Lichen', 'AL': 'Algae', 'OT': 'Other'}
        dist_labels = [category_map.get(d['category'], d['category']) for d in distribution]
        dist_data = [d['count'] for d in distribution]
        
        # Health status
        health_status = 'No Data'
        health_color = 'secondary'
        health_icon = 'question-circle'
        if latest_metrics:
            if latest_metrics.shannon_index >= 2.5:
                health_status, health_color, health_icon = 'Excellent', 'success', 'trophy'
            elif latest_metrics.shannon_index >= 1.5:
                health_status, health_color, health_icon = 'Good', 'info', 'chart-line'
            elif latest_metrics.shannon_index >= 0.8:
                health_status, health_color, health_icon = 'Moderate', 'warning', 'exclamation-triangle'
            else:
                health_status, health_color, health_icon = 'Critical', 'danger', 'skull-crossbones'
        
        context = {
            'total_species': total_species,
            'total_observations': total_observations,
            'today_observations': today_observations,
            'new_species_today': new_species_today,
            'latest_metrics': latest_metrics,
            'health_status': health_status,
            'health_color': health_color,
            'health_icon': health_icon,
            'active_alerts': active_alerts,
            'active_alerts_count': active_alerts_count,
            'recent_observations': recent_observations,
            'top_species': top_species,
            'max_observations': max_obs,
            'trend_labels': json.dumps(trend_labels),
            'trend_data': json.dumps(trend_data),
            'distribution_labels': json.dumps(dist_labels),
            'distribution_data': json.dumps(dist_data),
            'page_title': 'Dashboard',
        }
        return render(request, 'dashboard.html', context)
    
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        logger.error(traceback.format_exc())
        context = {
            'total_species': 0,
            'total_observations': 0,
            'today_observations': 0,
            'new_species_today': 0,
            'latest_metrics': None,
            'health_status': 'Error',
            'health_color': 'danger',
            'health_icon': 'exclamation-circle',
            'active_alerts': [],
            'active_alerts_count': 0,
            'recent_observations': [],
            'top_species': [],
            'max_observations': 1,
            'trend_labels': '[]',
            'trend_data': '[]',
            'distribution_labels': '[]',
            'distribution_data': '[]',
            'page_title': 'Dashboard',
        }
        return render(request, 'dashboard.html', context)


@login_required
def upload_image(request):
    """Handle image upload with AI detection"""
    if request.method == 'POST':
        form = ObservationUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                observation = form.save(commit=False)
                observation.observer = request.user
                
                # AI Detection
                ai_detected = False
                if observation.image:
                    try:
                        print(f"\n{'='*60}")
                        print(f"🤖 AI Detection Started")
                        print(f"📷 Image: {observation.image.name}")
                        print(f"📏 Size: {observation.image.size} bytes")
                        print(f"{'='*60}")
                        
                        # Initialize AI model
                        initialize_model()
                        
                        # Detect species
                        result = detect_species_from_image(observation.image)
                        
                        print(f"\n📊 AI Result:")
                        print(f"   Success: {result.get('success')}")
                        print(f"   Common Name: {result.get('common_name')}")
                        print(f"   Scientific Name: {result.get('scientific_name')}")
                        print(f"   Confidence: {result.get('confidence')}")
                        print(f"   Category: {result.get('category')}")
                        print(f"   Provider: {result.get('provider')}")
                        
                        # Check if detection was successful
                        if result and result.get('success') == True:
                            common_name = result.get('common_name', '')
                            scientific_name = result.get('scientific_name', '')
                            confidence = result.get('confidence', 0)
                            category = result.get('category', 'OT')
                            description = result.get('description', '')
                            
                            # Check if we got a valid species name
                            if common_name and common_name.lower() != 'unknown':
                                # Clean scientific name
                                if not scientific_name or scientific_name == 'unknown':
                                    scientific_name = common_name.lower().replace(' ', '_')
                                else:
                                    scientific_name = scientific_name.replace(' ', '_').lower()
                                
                                # Create or get species
                                species, created = Species.objects.get_or_create(
                                    scientific_name=scientific_name,
                                    defaults={
                                        'name': common_name,
                                        'category': category,
                                        'conservation_status': 'NE',
                                        'description': description
                                    }
                                )
                                
                                observation.species = species
                                observation.confidence_score = confidence * 100
                                observation.ai_verified = confidence > 0.7
                                ai_detected = True
                                
                                messages.success(
                                    request, 
                                    f'✅ AI Detected: {species.name} ({observation.confidence_score:.0f}% confidence)'
                                )
                                print(f"✅ Species saved: {species.name} (Created: {created})")
                            else:
                                print(f"⚠️ Unknown species detected")
                                messages.warning(request, '⚠️ Could not identify species. Please fill details manually.')
                        else:
                            error_msg = result.get('message', 'Could not identify species') if result else 'AI detection failed'
                            print(f"⚠️ Detection failed: {error_msg}")
                            messages.warning(request, f'⚠️ {error_msg}. Please fill details manually.')
                            
                    except Exception as e:
                        print(f"❌ AI Error: {e}")
                        traceback.print_exc()
                        messages.warning(request, f'⚠️ AI Error: {str(e)}. Please fill details manually.')
                else:
                    messages.info(request, 'Please upload an image for AI detection.')
                
                # Save the observation
                observation.save()
                print(f"\n💾 Observation saved: ID={observation.id}")
                
                # Update species count if species exists
                if observation.species:
                    observation.species.increment_detection_count()
                    print(f"📊 Updated species count for: {observation.species.name}")
                
                # Update user profile
                if hasattr(request.user, 'profile'):
                    request.user.profile.increment_observation_count()
                
                # Calculate metrics
                try:
                    calculate_biodiversity_metrics(timezone.now().date())
                    print(f"📈 Metrics calculated for {timezone.now().date()}")
                except Exception as e:
                    print(f"⚠️ Metrics calculation error: {e}")
                
                if not ai_detected and not observation.species:
                    messages.info(request, 'ℹ️ You can edit the observation to add species information later.')
                
                messages.success(request, '✅ Observation saved successfully!')
                return redirect('observation_detail', pk=observation.id)
                
            except Exception as e:
                print(f"❌ Save error: {e}")
                traceback.print_exc()
                messages.error(request, f'❌ Error saving observation: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ObservationUploadForm()
    
    return render(request, 'upload.html', {'form': form, 'page_title': 'Upload Observation'})


def species_list(request):
    """Display list of all species"""
    species_qs = Species.objects.all().order_by('name')
    
    # Search filter
    search = request.GET.get('search', '')
    if search:
        species_qs = species_qs.filter(
            Q(name__icontains=search) | 
            Q(scientific_name__icontains=search)
        )
    
    # Category filter
    category = request.GET.get('category', '')
    if category:
        species_qs = species_qs.filter(category=category)
    
    # Conservation status filter
    conservation = request.GET.get('conservation', '')
    if conservation:
        species_qs = species_qs.filter(conservation_status=conservation)
    
    # Pagination
    paginator = Paginator(species_qs, 20)
    page = request.GET.get('page', 1)
    species_page = paginator.get_page(page)
    
    context = {
        'species_list': species_page,
        'total_species': species_qs.count(),
        'search_query': search,
        'selected_category': category,
        'selected_conservation': conservation,
        'page_title': 'Species List',
    }
    return render(request, 'species_list.html', context)


def species_detail(request, pk):
    """Display detailed species information"""
    try:
        species = get_object_or_404(Species, pk=pk)
        observations = Observation.objects.filter(species=species).select_related('observer')[:20]
        stats = observations.aggregate(
            total=Count('id'), 
            avg_confidence=Avg('confidence_score'),
            first_seen=Min('timestamp'),
            last_seen=Max('timestamp')
        )
        
        context = {
            'species': species,
            'observations': observations,
            'stats': stats,
            'page_title': species.name,
        }
        return render(request, 'species_detail.html', context)
    except Exception as e:
        logger.error(f"Species detail error: {e}")
        messages.error(request, f'Error loading species details: {str(e)}')
        return redirect('species_list')


def observation_detail(request, pk):
    """Display observation details"""
    try:
        observation = get_object_or_404(Observation.objects.select_related('species', 'observer'), pk=pk)
        context = {
            'observation': observation, 
            'page_title': f'Observation #{observation.id}'
        }
        return render(request, 'observation_detail.html', context)
    except Exception as e:
        logger.error(f"Observation detail error: {e}")
        messages.error(request, f'Error loading observation: {str(e)}')
        return redirect('species_list')


def alerts_list(request):
    """Display list of alerts with severity breakdown"""
    try:
        alerts_qs = Alert.objects.all().order_by('-created_at')
        status = request.GET.get('status', 'active')
        
        if status == 'active':
            alerts_qs = alerts_qs.filter(is_resolved=False)
        elif status == 'resolved':
            alerts_qs = alerts_qs.filter(is_resolved=True)
        
        severity = request.GET.get('severity', '')
        if severity:
            alerts_qs = alerts_qs.filter(severity=severity)
        
        # Pagination
        paginator = Paginator(alerts_qs, 15)
        page = request.GET.get('page', 1)
        alerts_page = paginator.get_page(page)
        
        # Count alerts by status
        active_count = Alert.objects.filter(is_resolved=False).count()
        resolved_count = Alert.objects.filter(is_resolved=True).count()
        
        # Count alerts by severity for active alerts
        critical_count = Alert.objects.filter(is_resolved=False, severity='C').count()
        high_count = Alert.objects.filter(is_resolved=False, severity='H').count()
        medium_count = Alert.objects.filter(is_resolved=False, severity='M').count()
        low_count = Alert.objects.filter(is_resolved=False, severity='L').count()
        
        # Calculate average resolution time (in hours)
        resolved_alerts = Alert.objects.filter(
            is_resolved=True, 
            resolved_at__isnull=False
        )
        
        avg_time = 0
        if resolved_alerts.exists():
            total_seconds = 0
            for alert in resolved_alerts:
                delta = alert.resolved_at - alert.created_at
                total_seconds += delta.total_seconds()
            avg_seconds = total_seconds / resolved_alerts.count()
            avg_time = round(avg_seconds / 3600, 1)
        
        # Chart data - Last 30 days
        today = timezone.now().date()
        trend_labels = []
        trend_data = []
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            trend_labels.append(date.strftime('%b %d'))
            day_start = datetime.combine(date, datetime.min.time())
            day_start = timezone.make_aware(day_start)
            day_end = day_start + timedelta(days=1)
            count = Alert.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            trend_data.append(count)
        
        # Type distribution
        type_dist = Alert.objects.values('alert_type').annotate(count=Count('id'))
        type_map = {
            'SD': 'Species Decline', 
            'SI': 'Species Increase', 
            'NS': 'New Species',
            'RE': 'Rare Species', 
            'BD': 'Biodiversity Drop', 
            'BI': 'Biodiversity Increase',
            'INV': 'Invasive Species', 
            'THR': 'Threat Detected'
        }
        type_labels = [type_map.get(d['alert_type'], d['alert_type']) for d in type_dist]
        type_data = [d['count'] for d in type_dist]
        
        context = {
            'alerts': alerts_page,
            'current_status': status,
            'current_severity': severity,
            'active_alerts_count': active_count,
            'resolved_alerts_count': resolved_count,
            'critical_alerts_count': critical_count,
            'high_alerts_count': high_count,
            'medium_alerts_count': medium_count,
            'low_alerts_count': low_count,
            'avg_resolution_time': avg_time,
            'trend_labels': json.dumps(trend_labels),
            'trend_data': json.dumps(trend_data),
            'type_labels': json.dumps(type_labels),
            'type_data': json.dumps(type_data),
            'page_title': 'Alerts',
        }
        return render(request, 'alerts.html', context)
    except Exception as e:
        logger.error(f"Alerts list error: {e}")
        logger.error(traceback.format_exc())
        context = {
            'alerts': [],
            'current_status': 'active',
            'current_severity': '',
            'active_alerts_count': 0,
            'resolved_alerts_count': 0,
            'critical_alerts_count': 0,
            'high_alerts_count': 0,
            'medium_alerts_count': 0,
            'low_alerts_count': 0,
            'avg_resolution_time': 0,
            'trend_labels': '[]',
            'trend_data': '[]',
            'type_labels': '[]',
            'type_data': '[]',
            'page_title': 'Alerts',
        }
        return render(request, 'alerts.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def resolve_alert(request, pk):
    """Resolve an alert via AJAX"""
    try:
        alert = get_object_or_404(Alert, pk=pk)
        
        # Check if already resolved
        if alert.is_resolved:
            return JsonResponse({'success': False, 'error': 'Alert already resolved'}, status=400)
        
        # Get resolution notes
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            notes = data.get('notes', '')
        except:
            notes = ''
        
        # If no notes, use default
        if not notes:
            notes = f'Resolved by {request.user.username}'
        
        # Resolve the alert
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolution_notes = notes
        alert.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Alert resolved successfully',
            'alert_id': alert.id
        })
        
    except Alert.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Alert not found'}, status=404)
    except Exception as e:
        logger.error(f"Resolve alert error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def resolve_all_alerts(request):
    """Resolve all active alerts"""
    try:
        data = json.loads(request.body) if request.body else {}
        notes = data.get('notes', 'Resolved in bulk')
        
        alerts = Alert.objects.filter(is_resolved=False)
        count = alerts.count()
        
        for alert in alerts:
            alert.is_resolved = True
            alert.resolved_at = timezone.now()
            alert.resolution_notes = notes
            alert.save()
        
        return JsonResponse({'success': True, 'resolved_count': count})
    except Exception as e:
        logger.error(f"Resolve all alerts error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def biodiversity_report(request):
    """Generate biodiversity report - FIXED VERSION"""
    try:
        # Get date range from request
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Get ALL data counts (not filtered by date)
        total_species = Species.objects.count()
        total_observations = Observation.objects.count()
        
        # Get metrics for date range
        metrics = BiodiversityMetric.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Calculate days analyzed
        days_analyzed = (end_date - start_date).days + 1
        
        # Calculate summary statistics
        summary = {
            'total_observations': total_observations,
            'total_species': total_species,
            'period_observations': metrics.aggregate(Sum('total_observations'))['total_observations__sum'] or 0,
            'avg_shannon': metrics.aggregate(Avg('shannon_index'))['shannon_index__avg'] or 0,
            'avg_simpson': metrics.aggregate(Avg('simpson_index'))['simpson_index__avg'] or 0,
            'avg_richness': metrics.aggregate(Avg('species_richness'))['species_richness__avg'] or 0,
            'avg_evenness': metrics.aggregate(Avg('evenness'))['evenness__avg'] or 0,
        }
        
        context = {
            'metrics': metrics,
            'summary': summary,
            'start_date': start_date,
            'end_date': end_date,
            'days_analyzed': days_analyzed,
            'total_species': total_species,
            'total_observations': total_observations,
            'has_data': total_observations > 0,
            'has_metrics': metrics.exists(),
            'page_title': 'Biodiversity Report',
        }
        return render(request, 'biodiversity_report.html', context)
        
    except Exception as e:
        logger.error(f"Biodiversity report error: {e}")
        logger.error(traceback.format_exc())
        context = {
            'metrics': [],
            'summary': {},
            'total_species': Species.objects.count(),
            'total_observations': Observation.objects.count(),
            'has_data': Observation.objects.count() > 0,
            'has_metrics': False,
            'page_title': 'Biodiversity Report',
        }
        return render(request, 'biodiversity_report.html', context)


@csrf_exempt
def api_detect_species(request):
    """API endpoint for AJAX species detection"""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image = request.FILES['image']
            result = detect_species_from_image(image)
            print(f"API Detection Result: {result}")
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"API detection error: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'No image provided'}, status=400)


@csrf_exempt
def test_ai_detection(request):
    """Test AI detection without saving"""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image = request.FILES['image']
            result = detect_species_from_image(image)
            return JsonResponse({
                'success': result.get('success', False),
                'common_name': result.get('common_name', 'N/A'),
                'scientific_name': result.get('scientific_name', 'N/A'),
                'confidence': result.get('confidence', 0),
                'category': result.get('category', 'N/A'),
                'description': result.get('description', 'N/A'),
                'provider': result.get('provider', 'N/A'),
                'full_result': result
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'No image provided'}, status=400)


@csrf_exempt
def create_sample_alert(request):
    """Create a sample alert for testing with severity selection"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            title = data.get('title', 'Sample Alert')
            message = data.get('message', 'This is a sample alert for testing purposes.')
            severity = data.get('severity', 'M')
            alert_type = data.get('alert_type', 'BD')
            
            alert = Alert.objects.create(
                title=title,
                message=message,
                alert_type=alert_type,
                severity=severity,
                is_resolved=False
            )
            
            return JsonResponse({'success': True, 'alert_id': alert.id})
        except Exception as e:
            logger.error(f"Create sample alert error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


def alert_details_api(request, pk):
    """API endpoint for alert details modal"""
    try:
        alert = get_object_or_404(Alert, pk=pk)
        html = f"""
        <div class="alert-details">
            <h5>{alert.title}</h5>
            <hr>
            <p><strong>Type:</strong> {alert.get_alert_type_display()}</p>
            <p><strong>Severity:</strong> <span class="badge bg-{alert.severity_color}">{alert.get_severity_display()}</span></p>
            <p><strong>Message:</strong> {alert.message}</p>
            <p><strong>Created:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Status:</strong> {'Resolved' if alert.is_resolved else 'Active'}</p>
            {f'<p><strong>Resolved At:</strong> {alert.resolved_at.strftime("%Y-%m-%d %H:%M:%S")}</p>' if alert.resolved_at else ''}
            {f'<p><strong>Resolution Notes:</strong> {alert.resolution_notes}</p>' if alert.resolution_notes else ''}
            {f'<p><strong>Trigger Reason:</strong> {alert.trigger_reason or "Not specified"}</p>' if alert.trigger_reason else ''}
        </div>
        """
        return JsonResponse({'success': True, 'html': html})
    except Exception as e:
        logger.error(f"Alert details API error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def export_alerts(request):
    """Export alerts to CSV format"""
    try:
        status = request.GET.get('status', 'all')
        severity = request.GET.get('severity', '')
        alert_type = request.GET.get('type', '')
        
        alerts = Alert.objects.all()
        
        if status == 'active':
            alerts = alerts.filter(is_resolved=False)
        elif status == 'resolved':
            alerts = alerts.filter(is_resolved=True)
        
        if severity:
            alerts = alerts.filter(severity=severity)
        if alert_type:
            alerts = alerts.filter(alert_type=alert_type)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="alerts_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Title', 'Message', 'Type', 'Severity', 'Status', 'Created At', 'Resolved At', 'Resolution Notes'])
        
        for alert in alerts:
            writer.writerow([
                alert.id,
                alert.title,
                alert.message,
                alert.get_alert_type_display(),
                alert.get_severity_display(),
                'Resolved' if alert.is_resolved else 'Active',
                alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else '',
                alert.resolution_notes
            ])
        
        return response
    except Exception as e:
        logger.error(f"Export alerts error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def check_new_alerts(request):
    """Check for new alerts created in the last hour"""
    try:
        one_hour_ago = timezone.now() - timedelta(hours=1)
        new_alerts = Alert.objects.filter(
            created_at__gte=one_hour_ago,
            is_resolved=False
        )
        
        alerts_data = []
        for alert in new_alerts:
            alerts_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity
            })
        
        return JsonResponse({
            'success': True,
            'new_alerts_count': new_alerts.count(),
            'new_alerts': alerts_data
        })
    except Exception as e:
        logger.error(f"Check new alerts error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'species_count': Species.objects.count(),
        'observations_count': Observation.objects.count(),
        'alerts_count': Alert.objects.count(),
        'metrics_count': BiodiversityMetric.objects.count(),
    })


def ai_status(request):
    """Check AI model status"""
    try:
        model_info = get_model_info()
        return JsonResponse({
            'success': True,
            'ai_available': model_info.get('available', False),
            'provider': model_info.get('provider', 'none'),
            'model': model_info.get('model', 'N/A'),
            'api_key_configured': model_info.get('api_key_loaded', False),
            'mode': model_info.get('mode', 'unknown')
        })
    except Exception as e:
        logger.error(f"AI status error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', {'error': 'Page Not Found'}, status=404)


def custom_500(request):
    """Custom 500 error page"""
    return render(request, 'errors/500.html', {'error': 'Server Error'}, status=500)