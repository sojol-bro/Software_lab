# app/views.py

from datetime import timedelta

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.db.models.functions import TruncWeek
from django.http import FileResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from .forms import JobForm, JobQuizForm
from .models import (
    Choice, Job, Course, Company, CourseCategory,
    Enrollment, LessonCompletion, Lesson,
    Question, Quiz, QuizAttempt, UserAnswer, QuizCategory,
    UserProfile, Experience, Education, Skill, Project, Language, Certificate,
    JobQuiz
)


# =========================================================
# Helpers (safe auto-detect utilities used in employee_view)
# =========================================================
def _get_model(app_label, names):
    for n in names:
        try:
            return apps.get_model(app_label, n)
        except LookupError:
            continue
    return None


def _first_field(model, candidates):
    if not model:
        return None
    fields = {f.name for f in model._meta.get_fields()}
    for c in candidates:
        if c in fields:
            return c
    return None


def _get_user_type(request):
    """Return 'admin'/'employee'/'user' safely."""
    user_type = "user"
    try:
        cu = CustomUser.objects.get(user=request.user)
        user_type = cu.user_type
    except CustomUser.DoesNotExist:
        pass
    return user_type


# =========================================================
# Home / basic pages
# =========================================================
def home(request):
    featured_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:3]
    popular_courses = Course.objects.filter(is_active=True).order_by('-created_date')[:3]
    context = {
        'featured_jobs': featured_jobs,
        'popular_courses': popular_courses,
    }
    return render(request, 'welcome.html', context)


def about_view(request):
    return render(request, 'jobs/about.html')


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# =========================================================
# Account settings
# =========================================================
@login_required
def account_settings(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()

        if not username or not email:
            messages.error(request, 'Username and email are required.')
        else:
            if User.objects.exclude(id=request.user.id).filter(username=username).exists():
                messages.error(request, 'This username is already taken by another user.')
            elif User.objects.exclude(id=request.user.id).filter(email=email).exists():
                messages.error(request, 'This email is already used by another account.')
            else:
                request.user.username = username
                request.user.email = email
                request.user.save()
                messages.success(request, 'Account settings updated.')

        return redirect('app:account_settings')

    return render(request, 'profile/account_settings.html')


# =========================================================
# Jobs
# =========================================================
def job_list(request):
    jobs = Job.objects.filter(is_active=True).order_by('-posted_date')

    location_filter = request.GET.get('location', '')
    job_type_filter = request.GET.get('job_type', '')
    experience_filter = request.GET.get('experience', '')
    search_query = request.GET.get('q', '')

    if search_query:
        jobs = jobs.filter(title__icontains=search_query)

    if location_filter:
        if location_filter == 'remote':
            jobs = jobs.filter(work_mode='remote')
        else:
            jobs = jobs.filter(location__icontains=location_filter)

    if job_type_filter:
        jobs = jobs.filter(job_type=job_type_filter)

    if experience_filter:
        jobs = jobs.filter(experience_level=experience_filter)

    locations = Job.objects.filter(is_active=True).values_list('location', flat=True).distinct()
    job_types = Job.JOB_TYPES
    experience_levels = Job.EXPERIENCE_LEVELS

    context = {
        'jobs': jobs,
        'locations': locations,
        'job_types': job_types,
        'experience_levels': experience_levels,
        'selected_location': location_filter,
        'selected_job_type': job_type_filter,
        'selected_experience': experience_filter,
        'search_query': search_query,
    }
    return render(request, 'jobs/job_list.html', context)


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    return render(request, 'jobs/job_detail.html', {'job': job})


def search_jobs(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')

    jobs = Job.objects.filter(is_active=True)

    if query:
        jobs = jobs.filter(title__icontains=query)

    if location:
        jobs = jobs.filter(location__icontains=location)

    context = {'jobs': jobs, 'query': query, 'location': location}
    return render(request, 'jobs/job_search.html', context)


# =========================================================
# Employee job posting wizard (create -> quiz -> publish)
# =========================================================
@login_required
def create_job(request):
    user_type = _get_user_type(request)
    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
        return redirect('home')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.is_active = False
            job.save()
            messages.success(request, 'Job saved. Next, optionally add a quiz.')
            return redirect('app:build_job_quiz', job_id=job.id)
    else:
        form = JobForm()

    return render(request, 'jobs/job_form.html', {'form': form})


@login_required
def build_job_quiz(request, job_id):
    user_type = _get_user_type(request)
    if user_type not in ('employee', 'admin'):
        return redirect('home')

    job = get_object_or_404(Job, id=job_id)

    if request.method == 'POST':
        title = request.POST.get('quiz_title', '').strip() or f"Quiz for {job.title}"
        description = request.POST.get('quiz_description', '').strip()
        passing_score = int(request.POST.get('passing_score', '70') or 70)
        duration = int(request.POST.get('duration_minutes', '30') or 30)

        cat = QuizCategory.objects.first()
        if not cat:
            cat = QuizCategory.objects.create(name='General', description='Auto-created')

        quiz = Quiz.objects.create(
            title=title,
            category=cat,
            description=description,
            passing_score=passing_score,
            duration_minutes=duration,
        )

        # Parse dynamic questions
        q_indices = set()
        for key in request.POST.keys():
            if key.startswith('q-') and key.endswith('-text'):
                try:
                    q_indices.add(int(key.split('-')[1]))
                except Exception:
                    pass

        created_questions = 0
        for order_idx in sorted(q_indices):
            q_text = request.POST.get(f'q-{order_idx}-text', '').strip()
            q_type = request.POST.get(f'q-{order_idx}-type', 'multiple_choice')
            if not q_text:
                continue

            question = Question.objects.create(
                quiz=quiz,
                question_text=q_text,
                question_type=q_type,
                order=order_idx,
            )
            created_questions += 1

            # multiple_choice choices (optional)
            c_idx = 1
            while True:
                c_text = request.POST.get(f'q-{order_idx}-choice-{c_idx}-text')
                if c_text is None:
                    break
                c_text = c_text.strip()
                if c_text:
                    is_correct = request.POST.get(f'q-{order_idx}-choice-{c_idx}-correct') == 'on'
                    Choice.objects.create(
                        question=question,
                        choice_text=c_text,
                        is_correct=is_correct,
                    )
                c_idx += 1

        if created_questions == 0:
            quiz.delete()
            return redirect('app:build_job_quiz', job_id=job.id)

        JobQuiz.objects.update_or_create(job=job, defaults={'quiz': quiz})

        job.is_active = True
        job.posted_date = timezone.now()
        job.save()

        return redirect('app:publish_success', job_id=job.id)

    return render(request, 'jobs/quiz_builder.html', {'job': job})


@login_required
def add_job_quiz(request, job_id):
    user_type = _get_user_type(request)
    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
        return redirect('home')

    job = get_object_or_404(Job, id=job_id)

    if request.method == 'POST':
        form = JobQuizForm(request.POST)
        if form.is_valid():
            quiz = form.cleaned_data.get('quiz')
            if quiz:
                JobQuiz.objects.update_or_create(job=job, defaults={'quiz': quiz})
                messages.success(request, 'Quiz linked to job.')
            else:
                JobQuiz.objects.filter(job=job).delete()
                messages.info(request, 'No quiz selected. You can add one later.')
            return redirect('app:publish_job', job_id=job.id)
    else:
        initial = {}
        existing = JobQuiz.objects.filter(job=job).first()
        if existing:
            initial['quiz'] = existing.quiz
        form = JobQuizForm(initial=initial)

    return render(request, 'jobs/job_quiz_form.html', {'form': form, 'job': job})


@login_required
def publish_job(request, job_id):
    user_type = _get_user_type(request)
    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
        return redirect('home')

    job = get_object_or_404(Job, id=job_id)
    job_quiz = JobQuiz.objects.filter(job=job).select_related('quiz').first()

    if request.method == 'POST':
        if not job_quiz:
            messages.error(request, 'You must add a quiz before publishing this job.')
            return redirect('app:add_job_quiz', job_id=job.id)

        if not job_quiz.quiz.questions.exists():
            messages.error(request, 'Please add at least one question to the quiz before publishing.')
            return redirect('app:build_job_quiz', job_id=job.id)

        job.is_active = True
        job.save()
        return redirect('app:job_detail', job_id=job.id)

    return render(request, 'jobs/job_publish.html', {'job': job, 'job_quiz': job_quiz})


@login_required
def publish_success(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, "jobs/publish_success.html", {"job": job})


@login_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    jq = JobQuiz.objects.filter(job=job).select_related('quiz').first()

    if jq and jq.quiz:
        if not jq.quiz.questions.exists():
            messages.error(request, "This job's quiz is not ready yet. Please try again later.")
            return redirect('app:job_detail', job_id=job.id)

        existing_attempt = QuizAttempt.objects.filter(user=request.user, quiz=jq.quiz).first()
        if existing_attempt:
            existing_attempt.delete()

        attempt = QuizAttempt.objects.create(user=request.user, quiz=jq.quiz)
        return redirect('app:take_quiz', attempt_id=attempt.id)

    messages.success(request, 'Application submitted successfully.')
    return redirect('app:job_detail', job_id=job.id)


# =========================================================
# Courses
# =========================================================
def course_list(request):
    tab = request.GET.get('tab', 'all')

    if tab == 'all':
        courses = Course.objects.filter(is_active=True).order_by('-created_date')

        category_filter = request.GET.get('category', '')
        difficulty_filter = request.GET.get('difficulty', '')
        price_filter = request.GET.get('price', '')
        search_query = request.GET.get('q', '')

        if search_query:
            courses = courses.filter(
                Q(title__icontains=search_query) |
                Q(instructor__icontains=search_query) |
                Q(skills_covered__icontains=search_query)
            )

        if category_filter:
            courses = courses.filter(category__name=category_filter)

        if difficulty_filter:
            courses = courses.filter(difficulty=difficulty_filter)

        if price_filter:
            if price_filter == 'free':
                courses = courses.filter(price=0)
            elif price_filter == 'under_1000':
                courses = courses.filter(price__lt=1000)
            elif price_filter == 'over_1000':
                courses = courses.filter(price__gte=1000)

        categories = CourseCategory.objects.all()
        difficulty_levels = Course.DIFFICULTY_LEVELS

        context = {
            'courses': courses,
            'categories': categories,
            'difficulty_levels': difficulty_levels,
            'selected_category': category_filter,
            'selected_difficulty': difficulty_filter,
            'selected_price': price_filter,
            'search_query': search_query,
            'active_tab': tab,
            'show_filters': True,
        }

    elif tab == 'my_courses' and request.user.is_authenticated:
        enrollments = Enrollment.objects.filter(user=request.user).select_related('course')

        courses_with_progress = []
        total_lessons_completed = 0
        completed_courses_count = 0

        for enrollment in enrollments:
            progress_percentage = enrollment.get_progress_percentage()
            completed_lessons = enrollment.get_completed_lessons_count()
            total_lessons = enrollment.course.lessons.count()

            total_lessons_completed += completed_lessons
            if progress_percentage == 100:
                completed_courses_count += 1

            courses_with_progress.append({
                'enrollment': enrollment,
                'course': enrollment.course,
                'progress_percentage': progress_percentage,
                'completed_lessons': completed_lessons,
                'total_lessons': total_lessons,
                'next_lesson': enrollment.get_next_lesson(),
            })

        enrolled_course_ids = enrollments.values_list('course_id', flat=True)
        suggested_courses = Course.objects.filter(is_active=True).exclude(id__in=enrolled_course_ids)[:4]

        context = {
            'courses_with_progress': courses_with_progress,
            'suggested_courses': suggested_courses,
            'total_lessons_completed': total_lessons_completed,
            'completed_courses_count': completed_courses_count,
            'active_tab': tab,
            'show_filters': False,
        }

    else:
        return redirect('app:course_list')  # fallback

    return render(request, 'courses/course_list.html', context)


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    lessons = course.lessons.all().order_by('order')

    lessons_with_completion = []
    for lesson in lessons:
        completion = None
        if enrollment:
            completion = LessonCompletion.objects.filter(enrollment=enrollment, lesson=lesson).first()
        lessons_with_completion.append({'lesson': lesson, 'completion': completion})

    progress_percentage = enrollment.get_progress_percentage() if enrollment else 0

    related_courses = Course.objects.filter(category=course.category, is_active=True).exclude(id=course.id)[:3]
    instructor_courses_count = Course.objects.filter(instructor=course.instructor, is_active=True).count()

    context = {
        'course': course,
        'enrollment': enrollment,
        'lessons_with_completion': lessons_with_completion,
        'progress_percentage': progress_percentage,
        'related_courses': related_courses,
        'instructor_courses_count': instructor_courses_count,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)

    enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)

    if created:
        lessons = course.lessons.all()
        for lesson in lessons:
            LessonCompletion.objects.create(enrollment=enrollment, lesson=lesson, completed=False)
        messages.success(request, f'Successfully enrolled in {course.title}!')
    else:
        messages.info(request, f'You are already enrolled in {course.title}')

    return redirect('app:course_detail', course_id=course_id)


@login_required
def continue_learning(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    next_lesson = enrollment.get_next_lesson()
    if next_lesson:
        # ✅ your urls.py has learn_lesson, not lesson_detail
        return redirect('app:learn_lesson', course_id=course_id, lesson_id=next_lesson.id)

    messages.success(request, 'Congratulations! You have completed this course!')
    return redirect('app:course_detail', course_id=course_id)


@login_required
def learn_lesson(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course_id=course_id)

    context = {
        "course_id": course_id,
        "lesson_id": lesson_id,
        "course": course,
        "lesson": lesson,
    }
    return render(request, "courses/learn_lesson.html", context)


@login_required
def mark_lesson_complete(request, enrollment_id, lesson_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=enrollment.course)

    completion, created = LessonCompletion.objects.get_or_create(enrollment=enrollment, lesson=lesson)

    if not completion.completed:
        completion.completed = True
        completion.completed_date = timezone.now()
        completion.save()
        messages.success(request, f'Lesson "{lesson.title}" marked as completed!')
    else:
        messages.info(request, f'Lesson "{lesson.title}" was already completed')

    return redirect('app:course_detail', course_id=enrollment.course.id)


@login_required
def mark_lesson_complete_by_course(request, course_id, lesson_id):
    """
    Marks a lesson as completed for a given course (supports AJAX or normal POST).
    """
    if request.method == "POST":
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "course_id": course_id, "lesson_id": lesson_id})
        return redirect("app:learn_lesson", course_id=course_id, lesson_id=lesson_id)

    return HttpResponseRedirect(reverse("app:learn_lesson", args=[course_id, lesson_id]))


# =========================================================
# Course admin pages
# =========================================================
@login_required
def create_course(request):
    categories = CourseCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        instructor = request.POST.get('instructor')
        description = request.POST.get('description')
        short_description = request.POST.get('short_description')
        difficulty = request.POST.get('difficulty')
        price = request.POST.get('price')
        duration_weeks = request.POST.get('duration_weeks')
        lessons_count = request.POST.get('lessons_count')
        skills_covered = request.POST.get('skills_covered')

        thumbnail = request.FILES.get('thumbnail')
        instructor_photo = request.FILES.get('instructor_photo')

        category = CourseCategory.objects.get(id=category_id)
        Course.objects.create(
            title=title,
            category=category,
            instructor=instructor,
            description=description,
            short_description=short_description,
            difficulty=difficulty,
            price=price,
            duration_weeks=duration_weeks,
            lessons_count=lessons_count,
            skills_covered=skills_covered,
            thumbnail=thumbnail,
            instructor_photo=instructor_photo,
        )

        messages.success(request, "Course created successfully!")
        return redirect('app:create_admin')

    return render(request, 'courses/create_course.html', {'categories': categories})


@login_required
def create_admin(request):
    courses = Course.objects.filter(is_active=True).order_by('-created_date')
    categories = CourseCategory.objects.all()
    return render(request, 'courses/course_admin.html', {'courses': courses, 'categories': categories})


@login_required
def dashboard(request):
    return render(request, 'admin_dashboard.html')


# =========================================================
# Quizzes
# =========================================================
def quiz_list(request):
    quizzes = Quiz.objects.filter(is_active=True).order_by('-created_date')
    return render(request, 'quizzes/quiz_list.html', {'quizzes': quizzes})


def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    questions = quiz.questions.all().prefetch_related('choices')

    previous_attempt = None
    if request.user.is_authenticated:
        previous_attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz).first()

    context = {'quiz': quiz, 'questions': questions, 'previous_attempt': previous_attempt}
    return render(request, 'quizzes/quiz_detail.html', context)


@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)

    existing_attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz).first()

    if existing_attempt and existing_attempt.score > 40:
        messages.info(request, f'You have already attempted this quiz. Your score: {existing_attempt.score}%')
        return redirect('app:quiz_result', attempt_id=existing_attempt.id)

    if existing_attempt:
        existing_attempt.delete()

    attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)
    return redirect('app:take_quiz', attempt_id=attempt.id)


@login_required
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)

    if attempt.completed_at:
        messages.info(request, 'This quiz has already been completed.')
        return redirect('app:quiz_result', attempt_id=attempt.id)

    answered_question_ids = attempt.user_answers.values_list('question_id', flat=True)
    current_question = attempt.quiz.questions.exclude(id__in=answered_question_ids).first()

    if not current_question:
        return calculate_quiz_score(attempt)

    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        question = get_object_or_404(Question, id=question_id, quiz=attempt.quiz)

        if question.question_type == 'multiple_choice':
            choice_id = request.POST.get('choice_id')
            if choice_id:
                selected_choice = get_object_or_404(Choice, id=choice_id, question=question)
                is_correct = selected_choice.is_correct

                UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected_choice,
                    is_correct=is_correct
                )

        next_question = attempt.quiz.questions.exclude(
            id__in=attempt.user_answers.values_list('question_id', flat=True)
        ).first()

        if next_question:
            current_question = next_question
        else:
            return calculate_quiz_score(attempt)

    return render(request, 'quizzes/take_quiz.html', {'attempt': attempt, 'current_question': current_question})


def calculate_quiz_score(attempt):
    total_questions = attempt.quiz.questions.count()
    correct_answers = attempt.user_answers.filter(is_correct=True).count()

    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    attempt.score = score
    attempt.passed = score >= attempt.quiz.passing_score
    attempt.completed_at = timezone.now()
    attempt.save()

    attempt.quiz.attempts_count += 1
    attempt.quiz.save()

    return redirect('app:quiz_result', attempt_id=attempt.id)


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)

    if not attempt.completed_at:
        messages.error(request, 'Quiz not completed yet.')
        return redirect('app:take_quiz', attempt_id=attempt.id)

    for ua in attempt.user_answers.all():
        ua.correct_choices = ua.question.choices.filter(is_correct=True)

    context = {
        'attempt': attempt,
        'correct_answers': attempt.user_answers.filter(is_correct=True).count(),
        'total_questions': attempt.quiz.questions.count(),
    }
    return render(request, 'quizzes/quiz_result.html', context)


# =========================================================
# Profile
# =========================================================
@login_required
def profile(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user

    active_tab = request.GET.get('tab', 'overview')

    profile_obj, created = UserProfile.objects.get_or_create(user=profile_user)
    experiences = Experience.objects.filter(user=profile_user).order_by('-start_date')
    educations = Education.objects.filter(user=profile_user).order_by('-start_date')
    skills = Skill.objects.filter(user=profile_user).order_by('-percentage')
    projects = Project.objects.filter(user=profile_user).order_by('-start_date')
    languages = Language.objects.filter(user=profile_user)
    certificates = Certificate.objects.filter(user=profile_user).order_by('-issue_date')

    context = {
        'profile_user': profile_user,
        'profile': profile_obj,
        'experiences': experiences,
        'educations': educations,
        'skills': skills,
        'projects': projects,
        'languages': languages,
        'certificates': certificates,
        'active_tab': active_tab,
        'is_own_profile': profile_user == request.user,
    }
    return render(request, 'profile/profile.html', context)


@login_required
def edit_profile(request):
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile_obj.profile_picture = request.FILES['profile_picture']

        profile_obj.bio = request.POST.get('bio', '')
        profile_obj.title = request.POST.get('title', '')
        profile_obj.location = request.POST.get('location', '')
        profile_obj.phone = request.POST.get('phone', '')
        profile_obj.website = request.POST.get('website', '')
        profile_obj.linkedin = request.POST.get('linkedin', '')
        profile_obj.github = request.POST.get('github', '')
        profile_obj.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('app:profile')

    return render(request, 'profile/edit_profile.html', {'profile': profile_obj})


@login_required
def download_cv(request):
    profile_obj = get_object_or_404(UserProfile, user=request.user)
    if profile_obj.resume:
        return FileResponse(profile_obj.resume, as_attachment=True)

    messages.error(request, 'No resume uploaded yet.')
    return redirect('app:profile')


# =========================================================
# Missing views that your templates/urls are calling
# (fixes employer_profile + profile_router errors)
# =========================================================
@login_required
def profile_router(request):
    user_type = _get_user_type(request)

    if user_type == "admin":
        return redirect("app:admin_profile")
    elif user_type == "employee":
        return redirect("app:employer_profile")

    return redirect("app:profile")


@login_required
def employer_profile(request):
    user_type = _get_user_type(request)
    if user_type not in ("employee", "admin"):
        messages.error(request, "Access denied.")
        return redirect("app:profile")

    return render(request, "profile/employer_profile.html")


@login_required
def admin_profile(request):
    user_type = _get_user_type(request)
    if user_type != "admin":
        messages.error(request, "Access denied.")
        return redirect("app:profile")

    return render(request, "profile/admin_profile.html")


# =========================================================
# Employee dashboard view (if you still use this one)
# NOTE: your urls.py currently imports employee_view from accounts.views
# =========================================================
@login_required
def employee_view(request):
    user_type = _get_user_type(request)
    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
        return redirect('home')

    now = timezone.now()
    start_date = now - timedelta(weeks=8)

    jobs_week_labels, jobs_week_counts = [], []
    attempt_week_labels, attempt_week_counts = [], []

    jobs_weekly_qs = (
        Job.objects.filter(posted_date__gte=start_date)
        .annotate(week=TruncWeek("posted_date"))
        .values("week")
        .annotate(total=Count("id"))
        .order_by("week")
    )
    for row in jobs_weekly_qs:
        jobs_week_labels.append(row["week"].strftime("%b %d"))
        jobs_week_counts.append(row["total"])

    AttemptModel = _get_model("app", ["QuizAttempt", "Attempt", "QuizSubmission", "Submission", "QuizResult", "UserQuiz"])
    if AttemptModel:
        attempt_date_field = _first_field(
            AttemptModel,
            ["created_date", "created_at", "submitted_at", "attempted_at", "timestamp", "date_created"]
        )
        if attempt_date_field:
            attempts_weekly_qs = (
                AttemptModel.objects.filter(**{f"{attempt_date_field}__gte": start_date})
                .annotate(week=TruncWeek(attempt_date_field))
                .values("week")
                .annotate(total=Count("id"))
                .order_by("week")
            )
            for row in attempts_weekly_qs:
                attempt_week_labels.append(row["week"].strftime("%b %d"))
                attempt_week_counts.append(row["total"])

    ApplicationModel = _get_model("app", ["JobApplication", "Application", "ApplyJob", "JobApply", "CandidateApplication"])
    recent_applications = []
    if ApplicationModel:
        app_date_field = _first_field(
            ApplicationModel,
            ["created_date", "created_at", "applied_at", "submitted_at", "timestamp", "date_created"]
        )
        qs = ApplicationModel.objects.all()
        qs = qs.order_by(f"-{app_date_field}") if app_date_field else qs.order_by("-id")
        recent_applications = qs[:10]

    context = {
        'jobs_count': Job.objects.count(),
        'active_jobs_count': Job.objects.filter(is_active=True).count(),
        'quizzes_count': Quiz.objects.filter(is_active=True).count(),
        'courses_count': Course.objects.filter(is_active=True).count(),
        'latest_jobs': Job.objects.order_by('-posted_date')[:5],
        'latest_quizzes': Quiz.objects.order_by('-created_date')[:5],

        "jobs_week_labels": jobs_week_labels,
        "jobs_week_counts": jobs_week_counts,
        "attempt_week_labels": attempt_week_labels,
        "attempt_week_counts": attempt_week_counts,
        "recent_applications": recent_applications,
    }

    return render(request, 'employee/dashboard.html', context)
