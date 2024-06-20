from django.db import models
from auditlog.registry import auditlog

class Task(models.Model):
    execution_time = models.TimeField()
    description = models.TextField()
    last_execution = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Task: {self.description} scheduled for {self.next_execution}"

auditlog.register(Task)
