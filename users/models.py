from django.db import models
from django.contrib.auth.models import User
from main.models import Department, Faculty

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    faculty = models.ForeignKey(Faculty, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.user.username
