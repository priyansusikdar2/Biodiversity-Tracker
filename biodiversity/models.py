from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse

class Species(models.Model):
    """Species model for flora and fauna"""
    
    CATEGORY_CHOICES = [
        ('FL', 'Flora (Plants)'),
        ('FA', 'Fauna (Animals)'),
        ('FU', 'Fungi'),
        ('LI', 'Lichen'),
        ('AL', 'Algae'),
        ('OT', 'Other'),
    ]
    
    CONSERVATION_STATUS = [
        ('EX', 'Extinct'),
        ('EW', 'Extinct in Wild'),
        ('CR', 'Critically Endangered'),
        ('EN', 'Endangered'),
        ('VU', 'Vulnerable'),
        ('NT', 'Near Threatened'),
        ('LC', 'Least Concern'),
        ('DD', 'Data Deficient'),
        ('NE', 'Not Evaluated'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200, help_text="Common name of the species")
    scientific_name = models.CharField(max_length=300, unique=True, help_text="Scientific/Latin name")
    common_names = models.TextField(blank=True, help_text="Other common names (comma-separated)")
    description = models.TextField(blank=True, help_text="Description of the species")
    
    # Classification
    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES, default='FA')
    kingdom = models.CharField(max_length=100, blank=True)
    phylum = models.CharField(max_length=100, blank=True)
    class_name = models.CharField(max_length=100, blank=True, db_column='class')
    order = models.CharField(max_length=100, blank=True)
    family = models.CharField(max_length=100, blank=True)
    genus = models.CharField(max_length=100, blank=True)
    
    # Conservation
    conservation_status = models.CharField(max_length=2, choices=CONSERVATION_STATUS, default='NE')
    threat_factors = models.TextField(blank=True, help_text="Major threats to this species")
    is_native = models.BooleanField(default=True, help_text="Is this species native to the area?")
    
    # Statistics
    detection_count = models.IntegerField(default=0, help_text="Number of times detected")
    last_seen = models.DateTimeField(null=True, blank=True)
    confidence_threshold = models.FloatField(default=0.75, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Species'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['scientific_name']),
            models.Index(fields=['category', 'conservation_status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.scientific_name})"
    
    def get_absolute_url(self):
        return reverse('species_detail', args=[str(self.id)])
    
    def increment_detection_count(self):
        self.detection_count += 1
        self.last_seen = timezone.now()
        self.save(update_fields=['detection_count', 'last_seen'])
    
    @property
    def is_endangered(self):
        return self.conservation_status in ['CR', 'EN']
    
    @property
    def common_names_list(self):
        if self.common_names:
            return [name.strip() for name in self.common_names.split(',')]
        return []


class Observation(models.Model):
    """Model representing a single observation/sighting"""
    
    WEATHER_CHOICES = [
        ('CL', 'Clear/Sunny'),
        ('PC', 'Partly Cloudy'),
        ('CLD', 'Cloudy'),
        ('RN', 'Rainy'),
        ('FG', 'Foggy'),
        ('SN', 'Snowy'),
        ('WD', 'Windy'),
    ]
    
    HABITAT_CHOICES = [
        ('TF', 'Tropical Forest'),
        ('TMF', 'Temperate Forest'),
        ('BF', 'Boreal Forest'),
        ('MF', 'Mangrove Forest'),
        ('CF', 'Cloud Forest'),
        ('RF', 'Riparian Forest'),
        ('OT', 'Other'),
    ]
    
    # Relationships
    species = models.ForeignKey(Species, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations')
    observer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='observations')
    
    # Location data
    location = models.CharField(max_length=500, blank=True, help_text="Location description")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Image and AI data
    image = models.ImageField(upload_to='observations/%Y/%m/%d/', blank=True, null=True, help_text="Photo of the species")
    confidence_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    ai_verified = models.BooleanField(default=False)
    ai_model_version = models.CharField(max_length=50, blank=True)
    
    # Environmental data
    temperature = models.FloatField(null=True, blank=True, help_text="Temperature in Celsius")
    humidity = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    weather_condition = models.CharField(max_length=3, choices=WEATHER_CHOICES, blank=True)
    habitat_type = models.CharField(max_length=3, choices=HABITAT_CHOICES, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True, help_text="Observer's notes")
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['species', 'timestamp']),
            models.Index(fields=['observer', 'timestamp']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        species_name = self.species.name if self.species else "Unknown species"
        return f"{species_name} observed by {self.observer.username} at {self.timestamp}"
    
    def get_absolute_url(self):
        return reverse('observation_detail', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.species:
            self.species.increment_detection_count()
    
    @property
    def location_coordinates(self):
        if self.latitude and self.longitude:
            return (float(self.latitude), float(self.longitude))
        return None
    
    @property
    def image_url(self):
        return self.image.url if self.image else None


class Alert(models.Model):
    """Model for system alerts and notifications"""
    
    ALERT_TYPES = [
        ('SD', 'Species Decline'),
        ('SI', 'Species Increase'),
        ('NS', 'New Species'),
        ('RE', 'Rare Species Encountered'),
        ('BD', 'Biodiversity Drop'),
        ('BI', 'Biodiversity Increase'),
        ('INV', 'Invasive Species'),
        ('THR', 'Threat Detected'),
    ]
    
    SEVERITY_LEVELS = [
        ('L', 'Low'),
        ('M', 'Medium'),
        ('H', 'High'),
        ('C', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_type = models.CharField(max_length=3, choices=ALERT_TYPES, default='BD')
    severity = models.CharField(max_length=1, choices=SEVERITY_LEVELS, default='M')
    
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Trigger information
    trigger_reason = models.TextField(blank=True)
    related_species = models.ForeignKey(Species, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at', '-severity']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['alert_type', 'is_resolved']),
            models.Index(fields=['severity', 'is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"
    
    @property
    def severity_color(self):
        colors = {'L': 'info', 'M': 'warning', 'H': 'danger', 'C': 'dark'}
        return colors.get(self.severity, 'secondary')
    
    @property
    def severity_icon(self):
        icons = {'L': 'info-circle', 'M': 'exclamation-circle', 'H': 'exclamation-triangle', 'C': 'skull-crossbones'}
        return icons.get(self.severity, 'bell')
    
    def resolve(self, notes=""):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save(update_fields=['is_resolved', 'resolved_at', 'resolution_notes'])
        return True
    
    @classmethod
    def create_alert(cls, title, message, alert_type='BD', severity='M', related_species=None, trigger_reason=''):
        """Factory method to create a new alert"""
        return cls.objects.create(
            title=title,
            message=message,
            alert_type=alert_type,
            severity=severity,
            related_species=related_species,
            trigger_reason=trigger_reason
        )


class BiodiversityMetric(models.Model):
    """Model for storing calculated biodiversity metrics over time"""
    
    date = models.DateField(unique=True)
    
    # Diversity indices
    shannon_index = models.FloatField(help_text="Shannon-Wiener Diversity Index", default=0.0)
    simpson_index = models.FloatField(help_text="Simpson's Diversity Index", default=0.0)
    species_richness = models.IntegerField(help_text="Number of species observed", default=0)
    evenness = models.FloatField(help_text="Species evenness (Pielou's J)", default=0.0)
    
    # Population metrics
    total_observations = models.IntegerField(default=0)
    new_species_count = models.IntegerField(default=0)
    endangered_species_count = models.IntegerField(default=0)
    
    # Metadata
    calculation_method = models.CharField(max_length=100, default='Shannon-Wiener')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Biodiversity metrics'
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['date', 'shannon_index']),
        ]
    
    def __str__(self):
        return f"Metrics for {self.date}: H'={self.shannon_index:.2f}, S={self.species_richness}"
    
    @property
    def biodiversity_status(self):
        if self.shannon_index >= 3.0:
            return "Excellent"
        elif self.shannon_index >= 2.0:
            return "Good"
        elif self.shannon_index >= 1.0:
            return "Moderate"
        else:
            return "Poor"
    
    @property
    def biodiversity_color(self):
        if self.shannon_index >= 3.0:
            return "success"
        elif self.shannon_index >= 2.0:
            return "info"
        elif self.shannon_index >= 1.0:
            return "warning"
        else:
            return "danger"


class UserProfile(models.Model):
    """Extended user profile with additional fields"""
    
    ROLE_CHOICES = [
        ('RAN', 'Forest Ranger'),
        ('RES', 'Researcher'),
        ('VOL', 'Volunteer'),
        ('ADM', 'Administrator'),
        ('EDU', 'Educator'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=3, choices=ROLE_CHOICES, default='VOL')
    organization = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True, max_length=500)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True)
    
    total_observations = models.IntegerField(default=0)
    join_date = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    
    # Preferences
    notification_preferences = models.JSONField(default=dict, blank=True)
    default_location = models.CharField(max_length=500, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role', 'is_verified']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def increment_observation_count(self):
        self.total_observations += 1
        self.save(update_fields=['total_observations', 'last_active'])
    
    @property
    def get_role_icon(self):
        icons = {
            'RAN': 'tree',
            'RES': 'microscope',
            'VOL': 'hands-helping',
            'ADM': 'user-cog',
            'EDU': 'chalkboard-user'
        }
        return icons.get(self.role, 'user')