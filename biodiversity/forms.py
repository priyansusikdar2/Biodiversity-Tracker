from django import forms
from django.core.validators import FileExtensionValidator
from .models import Observation, Species, Alert

class ObservationUploadForm(forms.ModelForm):
    """
    Form for uploading new observations with AI detection
    """
    
    class Meta:
        model = Observation
        fields = ['image', 'location', 'latitude', 'longitude', 'temperature', 'humidity', 'weather_condition', 'habitat_type', 'notes']
        widgets = {
            'location': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Sundarbans Forest, Zone 3'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.0000001', 
                'placeholder': 'e.g., 21.9486'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.0000001', 
                'placeholder': 'e.g., 89.1833'
            }),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1', 
                'placeholder': '°C'
            }),
            'humidity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0, 
                'max': 100, 
                'placeholder': '%'
            }),
            'weather_condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'habitat_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Any additional observations...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': 'image/*'
            }),
        }
        help_texts = {
            'latitude': 'Use decimal degrees (e.g., 21.9486)',
            'longitude': 'Use decimal degrees (e.g., 89.1833)',
            'temperature': 'Temperature in degrees Celsius',
            'humidity': 'Relative humidity percentage',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom attributes
        self.fields['image'].required = True
        self.fields['image'].validators.append(
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'],
                message='Please upload a valid image file (JPG, JPEG, PNG, GIF, or WEBP)'
            )
        )
        
        # Mark location as required
        self.fields['location'].required = False
        
        # Add placeholder for weather and habitat
        self.fields['weather_condition'].choices = [('', 'Select Weather')] + list(Observation.WEATHER_CHOICES)
        self.fields['habitat_type'].choices = [('', 'Select Habitat')] + list(Observation.HABITAT_CHOICES)
    
    def clean_image(self):
        """Validate image file"""
        image = self.cleaned_data.get('image')
        
        if image:
            # Check file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Image size must be less than 10MB')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG, PNG, GIF, and WEBP images are allowed')
        
        return image
    
    def clean_coordinates(self):
        """Validate latitude and longitude combination"""
        latitude = self.cleaned_data.get('latitude')
        longitude = self.cleaned_data.get('longitude')
        
        # Either both provided or both empty
        if (latitude is not None and longitude is None) or (latitude is None and longitude is not None):
            raise forms.ValidationError('Both latitude and longitude must be provided together, or neither.')
        
        if latitude is not None:
            if latitude < -90 or latitude > 90:
                raise forms.ValidationError('Latitude must be between -90 and 90 degrees')
        
        if longitude is not None:
            if longitude < -180 or longitude > 180:
                raise forms.ValidationError('Longitude must be between -180 and 180 degrees')
        
        return latitude, longitude
    
    def clean_temperature(self):
        """Validate temperature range"""
        temperature = self.cleaned_data.get('temperature')
        
        if temperature is not None:
            if temperature < -50 or temperature > 60:
                raise forms.ValidationError('Temperature must be between -50°C and 60°C')
        
        return temperature
    
    def clean_humidity(self):
        """Validate humidity range"""
        humidity = self.cleaned_data.get('humidity')
        
        if humidity is not None:
            if humidity < 0 or humidity > 100:
                raise forms.ValidationError('Humidity must be between 0% and 100%')
        
        return humidity


class SpeciesFilterForm(forms.Form):
    """
    Form for filtering species list
    """
    
    category = forms.ChoiceField(
        required=False, 
        choices=[('', 'All Categories')] + list(Species.CATEGORY_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    conservation_status = forms.ChoiceField(
        required=False, 
        choices=[('', 'All Statuses')] + list(Species.CONSERVATION_STATUS),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or scientific name...',
            'aria-label': 'Search'
        })
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('name', 'Name'),
            ('detection_count', 'Detection Count'),
            ('last_seen', 'Last Seen'),
            ('scientific_name', 'Scientific Name')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class DateRangeForm(forms.Form):
    """
    Form for selecting date ranges for reports
    """
    
    start_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'placeholder': 'Start Date'
        })
    )
    
    end_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'placeholder': 'End Date'
        })
    )
    
    period = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Custom Range'),
            ('7', 'Last 7 days'),
            ('30', 'Last 30 days'),
            ('90', 'Last 90 days'),
            ('365', 'Last year'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        period = cleaned_data.get('period')
        
        from django.utils import timezone
        from datetime import timedelta
        
        # Handle preset periods
        if period:
            today = timezone.now().date()
            if period == '7':
                cleaned_data['start_date'] = today - timedelta(days=7)
                cleaned_data['end_date'] = today
            elif period == '30':
                cleaned_data['start_date'] = today - timedelta(days=30)
                cleaned_data['end_date'] = today
            elif period == '90':
                cleaned_data['start_date'] = today - timedelta(days=90)
                cleaned_data['end_date'] = today
            elif period == '365':
                cleaned_data['start_date'] = today - timedelta(days=365)
                cleaned_data['end_date'] = today
        
        # Get updated dates
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('Start date must be before end date')
        
        if start_date and start_date > timezone.now().date():
            raise forms.ValidationError('Start date cannot be in the future')
        
        return cleaned_data


class AlertResolutionForm(forms.ModelForm):
    """
    Form for resolving alerts with notes
    """
    
    class Meta:
        model = Alert
        fields = ['resolution_notes']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe how this alert was resolved...'
            })
        }
    
    def clean_resolution_notes(self):
        """Validate resolution notes"""
        notes = self.cleaned_data.get('resolution_notes')
        
        if not notes or len(notes.strip()) < 10:
            raise forms.ValidationError('Please provide detailed resolution notes (minimum 10 characters)')
        
        return notes.strip()


class BulkObservationForm(forms.Form):
    """
    Form for uploading multiple observations at once
    """
    
    observations_file = forms.FileField(
        required=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['csv', 'xlsx', 'xls'],
                message='Please upload a CSV or Excel file'
            )
        ],
        help_text='Upload CSV or Excel file with observations data',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    skip_ai_detection = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Skip AI detection and use provided species IDs',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_observations_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('observations_file')
        
        if file:
            # Check file size (max 50MB for bulk upload)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 50MB')
        
        return file


class QuickObservationForm(forms.Form):
    """
    Simple form for quick observations without AI
    """
    
    species_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter species name'
        })
    )
    
    location = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter location'
        })
    )
    
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional notes...'
        })
    )