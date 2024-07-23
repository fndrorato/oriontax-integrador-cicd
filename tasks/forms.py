# tasks/forms.py

from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['execution_time', 'description', 'last_execution', 'next_execution', 'frequency', 'days_of_week']

    frequency = forms.ChoiceField(choices=Task.FREQUENCY_CHOICES, widget=forms.Select())
    days_of_week = forms.MultipleChoiceField(choices=Task.DAYS_OF_WEEK_CHOICES, widget=forms.CheckboxSelectMultiple(), required=False)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.days_of_week = ','.join(self.cleaned_data['days_of_week'])
        if commit:
            instance.save()
        return instance    
