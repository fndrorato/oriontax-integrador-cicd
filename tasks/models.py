from django.db import models
from auditlog.registry import auditlog

class Task(models.Model):
    DAILY = 'D'
    WEEKLY = 'W'
    FREQUENCY_CHOICES = [
        (DAILY, 'Diariamente'),
        (WEEKLY, 'Semanalmente'),
    ]

    MONDAY = 'MO'
    TUESDAY = 'TU'
    WEDNESDAY = 'WE'
    THURSDAY = 'TH'
    FRIDAY = 'FR'
    SATURDAY = 'SA'
    SUNDAY = 'SU'
    DAYS_OF_WEEK_CHOICES = [
        (MONDAY, 'Segunda-Feira'),
        (TUESDAY, 'Terça-Feira'),
        (WEDNESDAY, 'Quarta-Feira'),
        (THURSDAY, 'Quinta-Feira'),
        (FRIDAY, 'Sexta-Feira'),
        (SATURDAY, 'Sábado'),
        (SUNDAY, 'Domingo'),
    ]
    
    execution_time = models.TimeField()
    description = models.TextField()
    last_execution = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)
    frequency = models.CharField(max_length=1, choices=FREQUENCY_CHOICES, default=DAILY)
    days_of_week = models.CharField(max_length=14, blank=True)  # Max length for storing all days
    

    def __str__(self):
        return f"Task: {self.description} scheduled for {self.next_execution}"

auditlog.register(Task)
