

from django.contrib import admin
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from accounts.views import employee_view

app_name = 'app'





urlpatterns = [
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('employee/jobs/create/', views.create_job, name='create_job'),
    path('employee/jobs/<int:job_id>/quiz-builder/', views.build_job_quiz, name='build_job_quiz'),
    path('employee/jobs/<int:job_id>/quiz/', views.add_job_quiz, name='add_job_quiz'),
    path('employee/jobs/<int:job_id>/publish/', views.publish_job, name='publish_job'),

    path('employee/jobs/<int:job_id>/published/', views.publish_success, name='publish_success'), #new added

    path('jobs/search/', views.search_jobs, name='search_jobs'),
    path('employee/dashboard/', employee_view, name='employee_dashboard'),

    path('create_course/', views.create_course, name='create_course'),
    path('course_admin/', views.create_admin, name='create_admin'),
    

    path('dashboard/', views.dashboard, name='dashboard'),

    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),

    path('courses/<int:course_id>/continue/', views.continue_learning, name='continue_learning'),
    path('courses/<int:course_id>/learn/<int:lesson_id>/', views.learn_lesson, name='learn_lesson'),

    path('enrollment/<int:enrollment_id>/lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('courses/<int:course_id>/lesson/<int:lesson_id>/complete/', views.mark_lesson_complete_by_course, name='mark_lesson_complete_by_course'),



    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quizzes/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quizzes/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('quiz/attempt/<int:attempt_id>/', views.take_quiz, name='take_quiz'),
    path('quiz/attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),

    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.profile, name='profile_view'),
    path('profile/download-cv/', views.download_cv, name='download_cv'),
    path('settings/', views.account_settings, name='account_settings'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
