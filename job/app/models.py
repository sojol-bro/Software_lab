from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class Company(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="companies",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Job(models.Model):
    JOB_TYPES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]
    
    EXPERIENCE_LEVELS = [
        ('entry', 'Entry-level'),
        ('mid', 'Mid-level'),
        ('senior', 'Senior'),
        ('top', 'Top-level'),
    ]
    
    WORK_MODES = [
        ('remote', 'Remote'),
        ('office', 'Office'),
        ('hybrid', 'Hybrid'),
    ]
    
    title = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    location = models.CharField(max_length=100)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='full_time')
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default='mid')
    work_mode = models.CharField(max_length=20, choices=WORK_MODES, default='office')
    description = models.TextField()
    requirements = models.TextField()
    skills_required = models.CharField(max_length=500)
    posted_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    category = models.CharField(max_length=100, default='General')
        
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    def get_salary_range(self):
        return f"${self.salary_min}k - ${self.salary_max}k"
    
    def get_skills_list(self):
        return [skill.strip() for skill in self.skills_required.split(',')]
    
    def get_formatted_date(self):
        return self.posted_date.strftime('%d/%m/%Y')
    
class CourseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Course(models.Model):
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    title = models.CharField(max_length=200)
    category = models.ForeignKey(CourseCategory, on_delete=models.CASCADE)
    instructor = models.CharField(max_length=100)
    instructor_photo = models.ImageField(upload_to='instructors/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_weeks = models.IntegerField()
    lessons_count = models.IntegerField()
    skills_covered = models.CharField(max_length=500)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    rating_count = models.IntegerField(default=0)
    students_count = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    def get_skills_list(self):
        return [skill.strip() for skill in self.skills_covered.split(',')]
    
    def get_difficulty_badge_class(self):
        if self.difficulty == 'beginner':
            return 'bg-green-200 text-green-800'
        elif self.difficulty == 'intermediate':
            return 'bg-blue-600 text-white'
        else:
            return 'bg-purple-200 text-purple-800'
    
    def get_background_class(self):
        colors = ['bg-blue-200', 'bg-blue-300', 'bg-blue-400', 'bg-green-200', 'bg-blue-100']
        index = self.id % len(colors) if self.id else 0
        return colors[index]

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()
    video_url = models.URLField(blank=True, null=True)
    duration_minutes = models.IntegerField()
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_date = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(default=timezone.now)  # Changed from auto_now=True
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
    
    def save(self, *args, **kwargs):
        # Update last_accessed when saving
        if not self.pk:  # New enrollment
            self.last_accessed = timezone.now()
        super().save(*args, **kwargs)
    
    def get_progress_percentage(self):
        """Calculate progress percentage based on completed lessons"""
        try:
            completed_lessons = LessonCompletion.objects.filter(
                enrollment=self, 
                completed=True
            ).count()
            total_lessons = self.course.lessons.count()
            if total_lessons == 0:
                return 0
            return int((completed_lessons / total_lessons) * 100)
        except:
            return 0
    
    def get_completed_lessons_count(self):
        try:
            return LessonCompletion.objects.filter(enrollment=self, completed=True).count()
        except:
            return 0
    
    def get_next_lesson(self):
        """Get the next uncompleted lesson"""
        try:
            completed_lessons = LessonCompletion.objects.filter(
                enrollment=self, 
                completed=True
            ).values_list('lesson_id', flat=True)
            
            next_lesson = self.course.lessons.exclude(id__in=completed_lessons).first()
            return next_lesson
        except:
            return None

class LessonCompletion(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['enrollment', 'lesson']
    
    def __str__(self):
        status = "Completed" if self.completed else "In Progress"
        return f"{self.enrollment.user.username} - {self.lesson.title} ({status})"
    


class QuizCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Quiz(models.Model):
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    title = models.CharField(max_length=200)
    category = models.ForeignKey(QuizCategory, on_delete=models.CASCADE)
    instructor = models.CharField(max_length=100, default='Saharier')
    instructor_photo = models.ImageField(upload_to='instructor_photos/', blank=True, null=True)
    description = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, default='beginner')
    duration_minutes = models.IntegerField(default=30)
    total_questions = models.IntegerField(default=10)
    passing_score = models.IntegerField(default=70)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    rating_count = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def get_difficulty_badge_class(self):
        if self.difficulty == 'beginner':
            return 'bg-green-500 text-white'
        elif self.difficulty == 'intermediate':
            return 'bg-yellow-500 text-white'
        else:
            return 'bg-red-500 text-white'
    
    def get_star_rating(self):
        """Return filled and empty stars based on rating"""
        filled_stars = int(self.rating)
        empty_stars = 5 - filled_stars
        return filled_stars, empty_stars

class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.choice_text

class JobQuiz(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='job_quiz')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.job.title} -> {self.quiz.title}"

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'quiz']
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"

class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    answer_text = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.question_text}"
    


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True)
    title = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Experience(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='experiences')
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.position} at {self.company}"

class Education(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.degree} at {self.institution}"

class Skill(models.Model):
    PROFICIENCY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS, default='intermediate')
    percentage = models.IntegerField(default=50)  # 0-100%
    
    def __str__(self):
        return f"{self.name} ({self.get_proficiency_display()})"

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    technologies = models.CharField(max_length=500)
    project_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def get_technologies_list(self):
        return [tech.strip() for tech in self.technologies.split(',')]

class Language(models.Model):
    PROFICIENCY_LEVELS = [
        ('basic', 'Basic'),
        ('conversational', 'Conversational'),
        ('professional', 'Professional'),
        ('native', 'Native'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='languages')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS, default='conversational')
    
    def __str__(self):
        return f"{self.name} ({self.get_proficiency_display()})"

class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    title = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=100, blank=True)
    credential_url = models.URLField(blank=True)
    
    def __str__(self):
        return self.title