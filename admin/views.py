from django.shortcuts import render
from accounts.models import CustomUser
from app.models import Job, Course

# Create your views here.
def admin_dashboard(request):
    total_users = CustomUser.objects.count()
    total_active_jobs = Job.objects.filter(is_active=True).count()
    total_courses = Course.objects.filter(is_active=True).count()
    recent_login_profiles = CustomUser.objects.select_related('user').order_by('-user__last_login')[:5]

    context = {
        'total_users': total_users,
        'total_active_jobs': total_active_jobs,
        'total_courses': total_courses,
        'recent_login_profiles': recent_login_profiles,
    }
    return render(request, 'admin_dashboard.html', context)

def admin_user(request):
    total_users = CustomUser.objects.count()
    total_active_jobs = Job.objects.filter(is_active=True).count()
    total_courses = Course.objects.filter(is_active=True).count()
    recent_login_profiles = CustomUser.objects.select_related('user').order_by('-user__last_login')[:5]

    context = {
        'total_users': total_users,
        'total_active_jobs': total_active_jobs,
        'total_courses': total_courses,
        'recent_login_profiles': recent_login_profiles,
    }
    return render(request, 'admin_item/admin-item.html',context)
def course_quiz(request):
    return render(request, 'quizzes/course_quiz.html')

