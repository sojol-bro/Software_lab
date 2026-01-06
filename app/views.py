from decimal import Decimal
from django.http import FileResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Choice, Job, Course, Company, CourseCategory,Course, CourseCategory, Enrollment,LessonCompletion,Lesson, Question, Quiz, QuizAttempt, UserAnswer, QuizCategory
from .models import UserProfile, Experience, Education, Skill, Project, Language, Certificate
from .models import JobQuiz
from .forms import JobForm, JobQuizForm
from accounts.models import CustomUser
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course, Enrollment, Payment
from .utils import prepare_course_detail_context
from .forms import PaymentForm




@login_required
def account_settings(request):
    # Basic account settings: username and email
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        # Validate simple constraints
        if not username or not email:
            messages.error(request, 'Username and email are required.')
        else:
            # Prevent username collision with other users
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



def home(request):

    featured_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:3]
    
    popular_courses = Course.objects.filter(is_active=True).order_by('-created_date')[:3]
    
    context = {
        'featured_jobs': featured_jobs,
        'popular_courses': popular_courses,
    }
    return render(request, 'welcome.html', context)

def job_list(request):
    jobs = Job.objects.filter(is_active=True).order_by('-posted_date')
    
    # Get filter parameters
    location_filter = request.GET.get('location', '')
    job_type_filter = request.GET.get('job_type', '')
    experience_filter = request.GET.get('experience', '')
    search_query = request.GET.get('q', '')
    
    # Apply filters
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
    
    # Get unique values for filter dropdowns
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
    context = {
        'job': job,
    }
    return render(request, 'jobs/job_detail.html', context)



def course_list(request):
    courses = Course.objects.filter(is_active=True).order_by('-created_date')
    categories = CourseCategory.objects.all()
    
    context = {
        'courses': courses,
        'categories': categories,
    }
    return render(request, 'courses/course_list.html', context)

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    context = {
        'course': course,
    }
    return render(request, 'courses/course_detail.html', context)
@login_required
def create_course(request):
    categories = CourseCategory.objects.all()

    if request.method == 'POST':
        # Extract data manually
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

        # Create course
        category = CourseCategory.objects.get(id=category_id)
        course = Course.objects.create(
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
        'categories': categories})

@login_required
def dashboard(request):
    return render(request, 'admin_dashboard.html')

def search_jobs(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    jobs = Job.objects.filter(is_active=True)
    
    if query:
        jobs = jobs.filter(title__icontains=query)
    
    if location:
        jobs = jobs.filter(location__icontains=location)
    
    context = {
        'jobs': jobs,
        'query': query,
        'location': location,
    }
    return render(request, 'jobs/job_search.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')



def course_list(request):
    # Determine active tab
    tab = request.GET.get('tab', 'all')
    
    # For "All Courses" tab
    if tab == 'all':
        courses = Course.objects.filter(is_active=True).order_by('-created_date')
        
        # Get filter parameters
        category_filter = request.GET.get('category', '')
        difficulty_filter = request.GET.get('difficulty', '')
        price_filter = request.GET.get('price', '')
        search_query = request.GET.get('q', '')
        
        # Apply filters
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
        
        # Get unique values for filter dropdowns
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
            'show_filters': True,  # Show filters for "All Courses"
        }
    
    # For "My Courses" tab
    elif tab == 'my_courses' and request.user.is_authenticated:
        enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
        
        # Calculate progress for each enrollment
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
        
        # Get suggested courses (excluding already enrolled ones)
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
            'show_filters': False,  # Hide filters for "My Courses"
        }
    
    else:
        # Default to "All Courses" if not authenticated or invalid tab
        return redirect('app:course_list?tab=all')
    
    return render(request, 'courses/course_list.html', context)



@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)

    # If already paid & enrolled, do not charge again
    if Enrollment.objects.filter(
        user=request.user,
        course=course,
        is_paid=True
    ).exists():
        messages.info(request, 'You are already enrolled in this course.')
        return redirect('app:course_detail', course_id=course_id)

    # Always go to payment
    return redirect('app:payment_page', course_id=course_id)


    

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Course, Enrollment
from django.db import transaction

@login_required
@transaction.atomic
def payment_success(request, course_id):
    # Get the course object
    course = get_object_or_404(Course, id=course_id, is_active=True)

    # Create or update the enrollment
    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={'is_paid': True}
    )

    # If the enrollment was created and payment was processed, show a success message
    if created:
        messages.success(request, 'Payment successful. You are now enrolled in the course.')
    else:
        # If the enrollment already exists but not paid, update the status
        if not enrollment.is_paid:
            enrollment.is_paid = True
            messages.success(request, 'Payment successful. Your enrollment is now confirmed.')
        else:
            messages.info(request, 'You are already enrolled in this course.')

    # Save changes and always redirect back to the course detail page
    try:
        enrollment.save()
        return redirect('app:course_detail', course_id=course_id)
    except Exception as e:
        messages.error(request, 'There was an error confirming your payment. Please try again.')
        return redirect('app:course_detail', course_id=course_id)


@login_required
def payment_page(request, course_id):
  
    course = get_object_or_404(Course, id=course_id, is_active=True)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    
    context = prepare_course_detail_context(course, enrollment)

    return render(request, 'Payments/First_stage_pay.html',context)


@login_required 
def goToPayment(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Save payment info
            payment = form.save(commit=False)
            payment.user = request.user  # Associate payment with the user
            payment.save()  # Save the payment record
            
            # Update enrollment status
            enrollment.is_paid = True
            enrollment.save()

            messages.success(request, 'Payment successful. You are now enrolled.')
            return redirect('app:payment_success', course_id=course_id)
    else:
        form = PaymentForm()

    context = prepare_course_detail_context(course, enrollment)
    context['form'] = form  # Add the form to the context
    return render(request, 'Payments/2nd_stage_pay.html', context)

@login_required
def my_courses(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
    
    # Calculate progress for each enrollment
    courses_with_progress = []
    for enrollment in enrollments:
        progress_percentage = enrollment.get_progress_percentage()
        completed_lessons = enrollment.get_completed_lessons_count()
        total_lessons = enrollment.course.lessons.count()
        
        courses_with_progress.append({
            'enrollment': enrollment,
            'course': enrollment.course,
            'progress_percentage': progress_percentage,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'next_lesson': enrollment.get_next_lesson(),
        })
    
    context = {
        'courses_with_progress': courses_with_progress,
        'active_tab': 'my_courses',
    }
    return render(request, 'courses/my_courses.html', context)

# views.py



@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    
    context = prepare_course_detail_context(course, enrollment)
    
    return render(request, 'courses/course_detail.html', context)




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
        return redirect('app:lesson_detail', course_id=course_id, lesson_id=next_lesson.id)
    else:
        messages.success(request, 'Congratulations! You have completed this course!')
        return redirect('app:course_detail', course_id=course_id)
    

def about_view(request):
    return render(request, 'jobs/about.html')


# ------- Employee job posting wizard -------
@login_required
def create_job(request):
    # Only employees/admins
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
            # Keep job unpublished until review/publish step
            job.is_active = False
            job.save()
            messages.success(request, 'Job saved. Next, optionally add a quiz.')
            return redirect('app:build_job_quiz', job_id=job.id)
    else:
        form = JobForm()
    return render(request, 'jobs/job_form.html', { 'form': form })

@login_required
def build_job_quiz(request, job_id):
    # Only employees/admins
    try:
        user_profile = CustomUser.objects.get(user=request.user)
        user_type = user_profile.user_type
    except CustomUser.DoesNotExist:
        user_type = 'user'
    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
        return redirect('home')

    job = get_object_or_404(Job, id=job_id)

    # On POST, create a new Quiz and its Questions/Choices based on the payload
    if request.method == 'POST':
        title = request.POST.get('quiz_title', '').strip() or f"Quiz for {job.title}"
        description = request.POST.get('quiz_description', '').strip()
        passing_score = int(request.POST.get('passing_score', '70') or 70)
        duration = int(request.POST.get('duration_minutes', '30') or 30)

        # Ensure a category exists
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
        # Expected fields: q-<idx>-text, q-<idx>-type, q-<idx>-choice-<n>-text, q-<idx>-choice-<n>-correct
        q_indices = set()
        for key in request.POST.keys():
            if key.startswith('q-') and key.endswith('-text'):
                try:
                    q_indices.add(int(key.split('-')[1]))
                except:
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
            # choices for multiple_choice
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
            # No questions created; do not publish, send back to builder
            quiz.delete()
            messages.error(request, 'Please add at least one question before saving the quiz.')
            return redirect('app:build_job_quiz', job_id=job.id)

        # Link job -> quiz via JobQuiz relation
        JobQuiz.objects.update_or_create(job=job, defaults={'quiz': quiz})
        # Auto-publish the job so it's visible to all users immediately
        job.is_active = True
        job.posted_date = timezone.now()
        job.save()
        messages.success(request, 'Quiz created, job published, and now visible to all users.')
        return redirect('app:job_detail', job_id=job.id)

    return render(request, 'jobs/quiz_builder.html', { 'job': job })

@login_required
def add_job_quiz(request, job_id):
    # Only employees/admins
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
                # If no quiz selected and one exists, remove it
                JobQuiz.objects.filter(job=job).delete()
                messages.info(request, 'No quiz selected. You can add one later.')
            return redirect('app:publish_job', job_id=job.id)
    else:
        # Preselect existing quiz if present
        initial = {}
        existing = JobQuiz.objects.filter(job=job).first()
        if existing:
            initial['quiz'] = existing.quiz
        form = JobQuizForm(initial=initial)

    return render(request, 'jobs/job_quiz_form.html', {
        'form': form,
        'job': job,
    })

@login_required
def publish_job(request, job_id):
    # Only employees/admins
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

    return render(request, 'jobs/job_publish.html', {
        'job': job,
        'job_quiz': job_quiz,
    })


@login_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    jq = JobQuiz.objects.filter(job=job).select_related('quiz').first()
    if jq and jq.quiz:
        if not jq.quiz.questions.exists():
            messages.error(request, 'This job\'s quiz is not ready yet. Please try again later.')
            return redirect('app:job_detail', job_id=job.id)
        # Always start a fresh attempt for this quiz when applying for the job
        existing_attempt = QuizAttempt.objects.filter(user=request.user, quiz=jq.quiz).first()
        if existing_attempt:
            existing_attempt.delete()
        attempt = QuizAttempt.objects.create(user=request.user, quiz=jq.quiz)
        return redirect('app:take_quiz', attempt_id=attempt.id)
    messages.success(request, 'Application submitted successfully.')
    return redirect('app:job_detail', job_id=job.id)



def quiz_list(request):
    quizzes = Quiz.objects.filter(is_active=True).order_by('-created_date')
    
    context = {
        'quizzes': quizzes,
    }
    return render(request, 'quizzes/quiz_list.html', context)

def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    questions = quiz.questions.all().prefetch_related('choices')
    
    # Check if user has already attempted this quiz
    previous_attempt = None
    if request.user.is_authenticated:
        previous_attempt = QuizAttempt.objects.filter(
            user=request.user, 
            quiz=quiz
        ).first()
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'previous_attempt': previous_attempt,
    }
    return render(request, 'quizzes/quiz_detail.html', context)

@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    
    # Check if user has already attempted this quiz
    existing_attempt = QuizAttempt.objects.filter(
        user=request.user, 
        quiz=quiz
    ).first()
    
    if existing_attempt and existing_attempt.score > 40:
        messages.info(request, f'You have already attempted this quiz. Your score: {existing_attempt.score}%')
        return redirect('app:quiz_result', attempt_id=existing_attempt.id)

    if existing_attempt :
        existing_attempt.delete()
    
    # Create new quiz attempt
    attempt = QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz
    )
    
    return redirect('app:take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    
    if attempt.completed_at:
        messages.info(request, 'This quiz has already been completed.')
        return redirect('app:quiz_result', attempt_id=attempt.id)
    
    # Get unanswered questions
    answered_question_ids = attempt.user_answers.values_list('question_id', flat=True)
    current_question = attempt.quiz.questions.exclude(id__in=answered_question_ids).first()
    
    if not current_question:
        # All questions answered, calculate score
        return calculate_quiz_score(attempt)
    
    if request.method == 'POST':
        # Process the answer
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
        elif question.question_type == 'true_false':
            answer = request.POST.get('answer') == 'true'
            # For true/false, we need to know the correct answer
            # This is a simplified version - you'd need to store correct answers differently
            pass
        
        # Get next question or finish quiz
        next_question = attempt.quiz.questions.exclude(
            id__in=attempt.user_answers.values_list('question_id', flat=True)
        ).first()
        
        if next_question:
            current_question = next_question
        else:
            return calculate_quiz_score(attempt)
    
    context = {
        'attempt': attempt,
        'current_question': current_question,
    }
    return render(request, 'quizzes/take_quiz.html', context)

def calculate_quiz_score(attempt):
    total_questions = attempt.quiz.questions.count()
    correct_answers = attempt.user_answers.filter(is_correct=True).count()
    
    if total_questions > 0:
        score = (correct_answers / total_questions) * 100
    else:
        score = 0
    
    attempt.score = score
    attempt.passed = score >= attempt.quiz.passing_score
    attempt.completed_at = timezone.now()
    attempt.save()
    
    # Update quiz statistics
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




@login_required
def profile(request, username=None):
    # If no username provided, show current user's profile
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user
    
    # Get active tab
    active_tab = request.GET.get('tab', 'overview')
    
    # Get profile data
    profile, created = UserProfile.objects.get_or_create(user=profile_user)
    experiences = Experience.objects.filter(user=profile_user).order_by('-start_date')
    educations = Education.objects.filter(user=profile_user).order_by('-start_date')
    skills = Skill.objects.filter(user=profile_user).order_by('-percentage')
    projects = Project.objects.filter(user=profile_user).order_by('-start_date')
    languages = Language.objects.filter(user=profile_user)
    certificates = Certificate.objects.filter(user=profile_user).order_by('-issue_date')
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
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
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        
        # Update other fields
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
    
    context = {
        'profile': profile,
    }
    return render(request, 'profile/edit_profile.html', context)

@login_required
def download_cv(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.resume:
        response = FileResponse(profile.resume, as_attachment=True)
        return response
    else:
        messages.error(request, 'No resume uploaded yet.')
        return redirect('app:profile')
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Job, Enrollment, QuizAttempt

@login_required
def employee_dashboard(request):
    user = request.user
    
    # Example data to show on dashboard
    jobs_applied = Job.objects.filter(company__job__job_quiz__quiz__quizattempt__user=user).distinct()
    courses_enrolled = request.user.enrollment_set.all()
    quizzes_attempted = QuizAttempt.objects.filter(user=user)
    
    context = {
        'jobs_applied': jobs_applied,
        'courses_enrolled': courses_enrolled,
        'quizzes_attempted': quizzes_attempted,
    }
    
    return render(request, 'employee_dashboard.html', context)
