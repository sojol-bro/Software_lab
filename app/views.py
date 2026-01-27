# views.py  ✅ (FULL CLEANED VERSION for your current code)
# - Adds profile_router()
# - Fixes employer template path (uses / not \)
# - Removes duplicate view definitions (job_detail/course_list/course_detail/enroll_course/dashboard/profile etc.)
# - Keeps your existing logic the same where possible

from django.http import FileResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods

from .models import (
    Choice, Job, Course, Company, CourseCategory,
    Enrollment, LessonCompletion, Lesson, Question, Quiz,
    QuizAttempt, UserAnswer, QuizCategory, UserProfile,
    Experience, Education, Skill, Project, Language, Certificate,
    JobQuiz
)
from .forms import JobForm, JobQuizForm
from accounts.models import CustomUser

UserModel = get_user_model()


# ---------------- HELPERS ----------------
def _get_or_create_userprofile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


# ---------------- ACCOUNT SETTINGS ----------------
@login_required
@require_http_methods(["GET", "POST"])
def account_settings(request):
    user = request.user
    profile = _get_or_create_userprofile(user)

    if request.method == "POST":
        action_type = (request.POST.get("action_type") or "").strip()

        # 1) ACCOUNT INFO
        if action_type == "account_info":
            first_name = (request.POST.get("first_name") or "").strip()
            last_name = (request.POST.get("last_name") or "").strip()
            username = (request.POST.get("username") or "").strip()
            email = (request.POST.get("email") or "").strip().lower()

            if not username:
                messages.error(request, "Username is required.")
                return redirect("app:account_settings")
            if not email:
                messages.error(request, "Email is required.")
                return redirect("app:account_settings")

            if UserModel.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
                messages.error(request, "This username is already taken.")
                return redirect("app:account_settings")

            if UserModel.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                messages.error(request, "This email is already in use.")
                return redirect("app:account_settings")

            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.email = email
            user.save()

            messages.success(request, "Account information updated.")
            return redirect("app:account_settings")

        # 2) PROFILE PICTURE (UserProfile.profile_picture)
        elif action_type == "profile_picture":
            if request.POST.get("remove_picture") == "1":
                if profile.profile_picture:
                    profile.profile_picture.delete(save=False)
                profile.profile_picture = None
                profile.save()
                messages.success(request, "Profile photo removed.")
                return redirect("app:account_settings")

            uploaded = request.FILES.get("profile_picture")
            if not uploaded:
                messages.error(request, "Please choose an image to upload.")
                return redirect("app:account_settings")

            max_size = 3 * 1024 * 1024
            if uploaded.size > max_size:
                messages.error(request, "Image too large. Please upload a file under 3MB.")
                return redirect("app:account_settings")

            profile.profile_picture = uploaded
            profile.save()
            messages.success(request, "Profile photo updated.")
            return redirect("app:account_settings")

        # 3) PASSWORD CHANGE
        elif action_type == "password_change":
            current_password = request.POST.get("current_password") or ""
            new_password1 = request.POST.get("new_password1") or ""
            new_password2 = request.POST.get("new_password2") or ""

            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("app:account_settings")

            if not new_password1 or not new_password2:
                messages.error(request, "Please enter and confirm your new password.")
                return redirect("app:account_settings")

            if new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
                return redirect("app:account_settings")

            try:
                validate_password(new_password1, user=user)
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
                return redirect("app:account_settings")

            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)

            messages.success(request, "Password updated successfully.")
            return redirect("app:account_settings")

        # 4) DELETE ACCOUNT
        elif action_type == "delete_account":
            confirm_text = (request.POST.get("confirm_text") or "").strip().upper()
            delete_password = request.POST.get("delete_password") or ""

            if confirm_text != "DELETE":
                messages.error(request, 'Type "DELETE" to confirm deletion.')
                return redirect("app:account_settings")

            if not user.check_password(delete_password):
                messages.error(request, "Password is incorrect.")
                return redirect("app:account_settings")

            logout(request)
            user.delete()
            messages.success(request, "Your account has been deleted.")
            return redirect("login")  # change if your login url name differs

        else:
            messages.error(request, "Unknown action.")
            return redirect("app:account_settings")

    return render(request, "profile/account_settings.html", {"profile": profile})


# ---------------- HOME ----------------
def home(request):
    featured_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:3]
    popular_courses = Course.objects.filter(is_active=True).order_by('-created_date')[:3]
    context = {
        'featured_jobs': featured_jobs,
        'popular_courses': popular_courses,
    }
    return render(request, 'welcome.html', context)


# ---------------- JOBS ----------------
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

    return render(request, 'jobs/job_search.html', {
        'jobs': jobs,
        'query': query,
        'location': location,
    })


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ---------------- COURSES ----------------
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

    return render(request, 'courses/create_course.html', {'categories': categories})


@login_required
def create_admin(request):
    courses = Course.objects.filter(is_active=True).order_by('-created_date')
    categories = CourseCategory.objects.all()
    return render(request, 'courses/course_admin.html', {
        'courses': courses,
        'categories': categories
    })


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
        suggested_courses = Course.objects.filter(is_active=True).exclude(
            id__in=enrolled_course_ids
        )[:4]

        context = {
            'courses_with_progress': courses_with_progress,
            'suggested_courses': suggested_courses,
            'total_lessons_completed': total_lessons_completed,
            'completed_courses_count': completed_courses_count,
            'active_tab': tab,
            'show_filters': False,
        }
    else:
        return redirect('app:course_list?tab=all')

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
            completion = LessonCompletion.objects.filter(
                enrollment=enrollment,
                lesson=lesson
            ).first()
        lessons_with_completion.append({'lesson': lesson, 'completion': completion})

    progress_percentage = enrollment.get_progress_percentage() if enrollment else 0

    related_courses = Course.objects.filter(
        category=course.category,
        is_active=True
    ).exclude(id=course.id)[:3]

    instructor_courses_count = Course.objects.filter(
        instructor=course.instructor,
        is_active=True
    ).count()

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

    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course
    )

    if created:
        lessons = course.lessons.all()
        for lesson in lessons:
            LessonCompletion.objects.create(
                enrollment=enrollment,
                lesson=lesson,
                completed=False
            )
        messages.success(request, f'Successfully enrolled in {course.title}!')
    else:
        messages.info(request, f'You are already enrolled in {course.title}')

    return redirect('app:course_detail', course_id=course_id)


@login_required
def mark_lesson_complete(request, enrollment_id, lesson_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=enrollment.course)

    completion, created = LessonCompletion.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )

    if not completion.completed:
        completion.completed = True
        completion.completed_date = timezone.now()
        completion.save()
        messages.success(request, f'Lesson "{lesson.title}" marked as completed!')
    else:
        messages.info(request, f'Lesson "{lesson.title}" was already completed')

    return redirect('app:course_detail', course_id=enrollment.course.id)


@login_required
def continue_learning(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    next_lesson = enrollment.get_next_lesson()
    if next_lesson:
        # NOTE: you don't currently have lesson_detail in urls.py
        # This will raise NoReverseMatch unless you create lesson_detail route.
        return redirect('app:lesson_detail', course_id=course_id, lesson_id=next_lesson.id)
    else:
        messages.success(request, 'Congratulations! You have completed this course!')
        return redirect('app:course_detail', course_id=course_id)


# ---------------- ABOUT ----------------
def about_view(request):
    return render(request, 'jobs/about.html')


# ---------------- EMPLOYEE JOB POSTING WIZARD ----------------
@login_required
def create_job(request):
    try:
        user_profile = CustomUser.objects.get(user=request.user)
        user_type = user_profile.user_type
    except CustomUser.DoesNotExist:
        user_type = 'user'

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
    try:
        user_profile = CustomUser.objects.get(user=request.user)
        user_type = user_profile.user_type
    except CustomUser.DoesNotExist:
        user_type = 'user'

    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
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
            messages.error(request, 'Please add at least one question before saving the quiz.')
            return redirect('app:build_job_quiz', job_id=job.id)

        JobQuiz.objects.update_or_create(job=job, defaults={'quiz': quiz})
        job.is_active = True
        job.posted_date = timezone.now()
        job.save()
        messages.success(request, 'Quiz created, job published, and now visible to all users.')
        return redirect('app:job_detail', job_id=job.id)

    return render(request, 'jobs/quiz_builder.html', {'job': job})


@login_required
def add_job_quiz(request, job_id):
    try:
        user_profile = CustomUser.objects.get(user=request.user)
        user_type = user_profile.user_type
    except CustomUser.DoesNotExist:
        user_type = 'user'

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
    try:
        user_profile = CustomUser.objects.get(user=request.user)
        user_type = user_profile.user_type
    except CustomUser.DoesNotExist:
        user_type = 'user'

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
        messages.success(request, 'Job published successfully!')
        return redirect('app:job_detail', job_id=job.id)

    return render(request, 'jobs/job_publish.html', {'job': job, 'job_quiz': job_quiz})


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


# ---------------- QUIZZES ----------------
def quiz_list(request):
    quizzes = Quiz.objects.filter(is_active=True).order_by('-created_date')
    return render(request, 'quizzes/quiz_list.html', {'quizzes': quizzes})


def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    questions = quiz.questions.all().prefetch_related('choices')

    previous_attempt = None
    if request.user.is_authenticated:
        previous_attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz).first()

    return render(request, 'quizzes/quiz_detail.html', {
        'quiz': quiz,
        'questions': questions,
        'previous_attempt': previous_attempt,
    })


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

    return render(request, 'quizzes/take_quiz.html', {
        'attempt': attempt,
        'current_question': current_question,
    })


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

    return render(request, 'quizzes/quiz_result.html', {
        'attempt': attempt,
        'correct_answers': attempt.user_answers.filter(is_correct=True).count(),
        'total_questions': attempt.quiz.questions.count(),
    })


# ---------------- PROFILE ROUTER + PROFILES ----------------
@login_required
def profile_router(request):
    """
    Redirect user to correct profile page based on role:
    admin -> admin_profile
    employee -> employer_profile
    user -> profile
    """
    try:
        role = request.user.customuser.user_type
    except Exception:
        role = "user"

    if role == "admin":
        return redirect("app:admin_profile")
    elif role == "employee":
        return redirect("app:employer_profile")
    return redirect("app:profile")


@login_required
def profile(request, username=None):
    if username:
        target_custom_user = get_object_or_404(CustomUser, user__username=username)
        actual_user_obj = target_custom_user.user
    else:
        actual_user_obj = request.user

    try:
        viewer_custom_user = CustomUser.objects.get(user=request.user)
        viewer_role = viewer_custom_user.user_type
    except CustomUser.DoesNotExist:
        viewer_role = 'user'

    profile_info, created = UserProfile.objects.get_or_create(user=actual_user_obj)

    experiences = Experience.objects.filter(user=actual_user_obj).order_by('-start_date')
    educations = Education.objects.filter(user=actual_user_obj).order_by('-start_date')
    skills = Skill.objects.filter(user=actual_user_obj).order_by('-percentage')
    projects = Project.objects.filter(user=actual_user_obj).order_by('-start_date')
    certificates = Certificate.objects.filter(user=actual_user_obj).order_by('-issue_date')
    languages = Language.objects.filter(user=actual_user_obj)

    context = {
        'profile_user': actual_user_obj,
        'profile': profile_info,
        'viewer_role': viewer_role,
        'experiences': experiences,
        'educations': educations,
        'skills': skills,
        'projects': projects,
        'certificates': certificates,
        'languages': languages,
        'active_tab': request.GET.get('tab', 'overview'),
        'is_own_profile': actual_user_obj == request.user,
    }

    return render(request, 'profile/profile.html', context)


@login_required
def edit_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']

        profile.bio = request.POST.get('bio', '')
        profile.title = request.POST.get('title', '')
        profile.location = request.POST.get('location', '')
        profile.phone = request.POST.get('phone', '')
        profile.website = request.POST.get('website', '')
        profile.linkedin = request.POST.get('linkedin', '')
        profile.github = request.POST.get('github', '')
        profile.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('app:profile')

    return render(request, 'profile/edit_profile.html', {'profile': profile})


@login_required
def download_cv(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.resume:
        return FileResponse(profile.resume, as_attachment=True)
    messages.error(request, 'No resume uploaded yet.')
    return redirect('app:profile')


@login_required
def employer_profile(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user

    context = {
        "profile_user": profile_user,
        "company": getattr(profile_user, "company", None),
        "company_stats": {},
        "jobs": [],
        "quizzes": [],
        "applicants": [],
        "team_members": [],
        "reviews": [],
        "active_tab": request.GET.get("tab", "overview"),
        "is_company_owner": True,
    }

    # ✅ FIXED PATH (use /)
    return render(request, "profile/employer_profile.html", context)


@login_required
def admin_profile(request):
    return render(request, "profile/admin_profile.html")


# ---------------- DASHBOARDS / ADMIN ----------------
@login_required
def employee_dashboard(request):
    user = request.user

    jobs_applied = Job.objects.filter(company__job__job_quiz__quiz__quizattempt__user=user).distinct()
    courses_enrolled = request.user.enrollment_set.all()
    quizzes_attempted = QuizAttempt.objects.filter(user=user)

    context = {
        'jobs_applied': jobs_applied,
        'courses_enrolled': courses_enrolled,
        'quizzes_attempted': quizzes_attempted,
    }

    return render(request, 'employee_dashboard.html', context)


@login_required
def dashboard(request):
    total_users = CustomUser.objects.count()
    total_active_jobs = Job.objects.filter(is_active=True).count()
    total_courses = Course.objects.filter(is_active=True).count()

    recent_login_profiles = CustomUser.objects.all().order_by('-user__last_login')[:10]

    context = {
        'total_users': total_users,
        'total_active_jobs': total_active_jobs,
        'total_courses': total_courses,
        'recent_login_profiles': recent_login_profiles,
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def manage_users(request):
    try:
        current_profile = CustomUser.objects.get(user=request.user)
        if current_profile.user_type != 'admin':
            messages.error(request, 'Access denied.')
            return redirect('home')
    except CustomUser.DoesNotExist:
        return redirect('home')

    query = request.GET.get('q', '')
    if query:
        all_users = CustomUser.objects.filter(
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        ).order_by('-user__date_joined')
    else:
        all_users = CustomUser.objects.all().order_by('-user__date_joined')

    return render(request, 'admin_item/manage_users.html', {
        'all_users': all_users,
        'query': query,
    })


@login_required
def toggle_user_status(request, user_id):
    current_profile = CustomUser.objects.get(user=request.user)
    if current_profile.user_type != 'admin':
        return redirect('home')

    user_to_change = get_object_or_404(User, id=user_id)
    user_to_change.is_active = not user_to_change.is_active
    user_to_change.save()

    status_msg = "unblocked" if user_to_change.is_active else "blocked"
    messages.success(request, f"User {user_to_change.username} has been {status_msg} successfully.")

    return redirect('app:manage_users')
