from django.contrib import admin
from .models import Choice, Company, Job, CourseCategory, Course, Enrollment, Question, Quiz, QuizAttempt, QuizCategory, UserAnswer
from .models import UserProfile, Experience, Education, Skill, Project, Language, Certificate

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'experience_level', 'work_mode', 'job_type', 'salary_min', 'salary_max', 'posted_date', 'is_active']
    list_filter = ['job_type', 'experience_level', 'work_mode', 'is_active', 'posted_date']
    search_fields = ['title', 'company__name', 'location', 'skills_required']
    list_editable = ['is_active']

@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'instructor', 'price', 'difficulty', 'rating', 'students_count', 'is_active']
    list_filter = ['category', 'difficulty', 'is_active', 'created_date']
    search_fields = ['title', 'instructor', 'skills_covered']
    list_editable = ['is_active', 'price']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'enrolled_date', 'completed']
    list_filter = ['completed', 'enrolled_date']
    search_fields = ['user__username', 'course__title']


@admin.register(QuizCategory)
class QuizCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'instructor', 'difficulty', 'duration_minutes', 'rating', 'attempts_count', 'is_active']
    list_filter = ['category', 'difficulty', 'is_active', 'created_date']
    search_fields = ['title', 'instructor']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'quiz', 'question_type', 'order', 'points']
    list_filter = ['quiz', 'question_type']
    search_fields = ['question_text']

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['choice_text', 'question', 'is_correct']
    list_filter = ['question__quiz', 'is_correct']
    search_fields = ['choice_text']

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'started_at', 'completed_at', 'score', 'passed']
    list_filter = ['quiz', 'passed', 'started_at']
    search_fields = ['user__username', 'quiz__title']

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'is_correct']
    list_filter = ['is_correct']
    search_fields = ['attempt__user__username', 'question__question_text']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'location', 'phone']
    search_fields = ['user__username', 'user__email', 'title']

@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ['user', 'position', 'company', 'start_date', 'end_date', 'current']
    list_filter = ['current', 'start_date']
    search_fields = ['user__username', 'position', 'company']

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ['user', 'degree', 'institution', 'start_date', 'end_date', 'current']
    list_filter = ['current', 'start_date']
    search_fields = ['user__username', 'degree', 'institution']

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'proficiency', 'percentage']
    list_filter = ['proficiency']
    search_fields = ['user__username', 'name']

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'start_date', 'end_date']
    search_fields = ['user__username', 'title', 'technologies']

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'proficiency']
    list_filter = ['proficiency']
    search_fields = ['user__username', 'name']

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'issuing_organization', 'issue_date']
    search_fields = ['user__username', 'title', 'issuing_organization']