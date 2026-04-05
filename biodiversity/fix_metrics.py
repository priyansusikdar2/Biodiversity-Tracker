"""
Management command to fix biodiversity metrics
Usage: python manage.py fix_metrics
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from biodiversity.models import Observation, BiodiversityMetric
from biodiversity.utils import calculate_biodiversity_metrics

class Command(BaseCommand):
    help = 'Recalculate biodiversity metrics for all dates with observations'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, help='Number of days to recalculate (default: all)')
        parser.add_argument('--date', type=str, help='Specific date to recalculate (YYYY-MM-DD)')

    def handle(self, *args, **options):
        self.stdout.write("🔄 Recalculating biodiversity metrics...")
        
        if options['date']:
            from datetime import datetime
            date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            metric = calculate_biodiversity_metrics(date)
            self.stdout.write(self.style.SUCCESS(f"✓ Recalculated metrics for {date}"))
            return
        
        # Get all dates with observations
        dates = Observation.objects.dates('timestamp', 'day')
        
        if options['days']:
            cutoff = timezone.now().date() - timedelta(days=options['days'])
            dates = [d for d in dates if d >= cutoff]
        
        fixed_count = 0
        for date in dates:
            try:
                calculate_biodiversity_metrics(date)
                fixed_count += 1
                self.stdout.write(f"  ✓ {date}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ {date}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Fixed {fixed_count} days of metrics"))