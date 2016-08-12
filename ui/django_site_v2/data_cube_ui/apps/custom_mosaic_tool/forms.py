from django import forms

import datetime

from .models import Satellite

# Author: AHDS
# Creation date: 2016-06-23
# Modified by:
# Last modified date:

years_range = list(range(1990, datetime.datetime.now().year+1))

class DataSelectForm(forms.Form):
    #these are done in the init funct.
    result_type = forms.ChoiceField(label='Result Type (Map view/png):', widget=forms.Select(attrs={'class': 'field-long'}))
    band_selection = forms.MultipleChoiceField(label="Band Selection (Data output/GTiff):", widget=forms.SelectMultiple(attrs={'class': 'multiselect field-long'}))
    title = forms.CharField(widget=forms.HiddenInput())
    description = forms.CharField(widget=forms.HiddenInput())
    def __init__(self, result_list=None, band_list=None, *args, **kwargs):
        super(DataSelectForm, self).__init__(*args, **kwargs)
        if result_list is not None and band_list is not None:
            self.fields["result_type"] = forms.ChoiceField(help_text='Select the type of image you would like displayed.', label='Result Type (Map view/png):', choices=result_list, widget=forms.Select(attrs={'class': 'field-long tooltipped'}))
            self.fields["band_selection"] = forms.MultipleChoiceField(help_text='Select any bands you would like in the GeoTiff output.', label="Band Selection (Data output/GTiff):", widget=forms.SelectMultiple(attrs={'class': 'multiselect field-long tooltipped'}), choices=band_list)

class GeospatialForm(forms.Form):
    latitude_min = forms.FloatField(label='Min Latitude', widget = forms.NumberInput(attrs={'class': 'field-divided', 'step': "any", 'required': 'required'}))
    latitude_max = forms.FloatField(label='Max Latitude', widget = forms.NumberInput(attrs={'class': 'field-divided', 'step': "any", 'required': 'required'}))
    longitude_min = forms.FloatField(label='Min Longitude', widget = forms.NumberInput(attrs={'class': 'field-divided', 'step': "any", 'required': 'required'}))
    longitude_max = forms.FloatField(label='Max Longitude', widget = forms.NumberInput(attrs={'class': 'field-divided', 'step': "any", 'required': 'required'}))
    time_start = forms.DateField(label='Start Date', widget=forms.DateInput(attrs={'class': 'datepicker field-divided', 'placeholder': '01/01/2010', 'required': 'required'}))
    time_end = forms.DateField(label='End Date', widget=forms.DateInput(attrs={'class': 'datepicker field-divided', 'placeholder': '01/02/2010', 'required': 'required'}))
