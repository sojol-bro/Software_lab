from django.contrib.auth.models import User
from django.db import models

class CustomUser(models.Model):
    USER_TYPES = (
        ('user', 'Regular User'),     # Job Seeker
        ('employee', 'Employee'),     # Employer / Company
        ('admin', 'Administrator'),   # Admin
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"