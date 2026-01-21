from django.urls import path
from . import views


urlpatterns = [
    path('',views.admin_dashboard, name='admin_dashboard'),
    path('admin_user/',views.admin_user, name='admin_user'),
    path('course_quiz/', views.course_quiz, name='course_quiz'),

    


]
