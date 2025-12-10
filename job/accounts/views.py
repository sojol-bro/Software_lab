from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

from .utils import create_otp_for_user, send_email_otp, send_sms_otp, verify_totp
from .models import OTP

from .models import CustomUser
from django.contrib.auth.decorators import login_required
from app.models import Job, Quiz, Course
 
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')
        
        # Validate required fields
        if not username or not email or not password or not confirm_password or not user_type:
            messages.error(request, 'All fields are required.')
            return render(request, 'auth/signup.html')
            
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/signup.html')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/signup.html')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/signup.html')
        
        # Validate user type
        valid_user_types = ['user', 'employee', 'admin']
        if user_type not in valid_user_types:
            messages.error(request, 'Invalid user type selected.')
            return render(request, 'auth/signup.html')
        
        try:
            # Validate password using Django validators and our custom validator
            validate_password(password)
            # Create user
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # Create user profile
            CustomUser.objects.create(user=user, user_type=user_type)
            
            # Set staff status for admins
            if user_type == 'admin':
                user.is_staff = True
                user.save()
            
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {username}.')
            if user_type == 'admin':
                messages.success(request, 'Welcome back, Administrator!')
                return redirect('admin_dashboard')
            elif user_type == 'employee':
                messages.success(request, 'Welcome back, Employee!')
                return redirect('employee_view')
            else:
                messages.success(request, 'Welcome back!')
                return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'auth/signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        # Find user for lockout checks
        user_qs = User.objects.filter(username=username)
        if not user_qs.exists():
            messages.error(request, 'Invalid username or password.')
            return render(request, 'auth/login.html')

        user_obj = user_qs.first()

        try:
            profile = CustomUser.objects.get(user=user_obj)
        except CustomUser.DoesNotExist:
            profile = None

        # Lockout check
        if profile and profile.is_locked():
            messages.error(request, f'Account locked until {profile.lockout_until}. Please try later or contact support.')
            return render(request, 'auth/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Password correct — reset failed attempts
            if profile:
                profile.reset_failed_attempts()

            # If the user has 2FA enabled, start the challenge instead of logging in straight away
            if profile and profile.two_factor_enabled:
                # Email or SMS OTP
                if profile.two_factor_method in ('email', 'sms'):
                    channel = profile.two_factor_method
                    otp_rec = create_otp_for_user(user, channel=channel)
                    if channel == 'email':
                        send_email_otp(user, otp_rec)
                    else:
                        send_sms_otp(user, otp_rec)

                    # store temp session state until they verify OTP
                    request.session['pre_2fa_user_id'] = user.id
                    request.session['pre_2fa_otp_id'] = str(otp_rec.id)
                    request.session['pre_2fa_method'] = channel
                    return redirect('two_factor_challenge')

                # TOTP (Authenticator app)
                if profile.two_factor_method == 'totp':
                    request.session['pre_2fa_user_id'] = user.id
                    request.session['pre_2fa_method'] = 'totp'
                    return redirect('two_factor_challenge')

            # No 2FA — complete login
            login(request, user)

            # Get user profile to check user type
            try:
                user_profile = CustomUser.objects.get(user=user)
                user_type = user_profile.user_type
            except CustomUser.DoesNotExist:
                # Fallback if profile doesn't exist
                user_type = 'user'

            # Redirect based on user type
            if user_type == 'admin':
                messages.success(request, 'Welcome back, Administrator!')
                return redirect('admin_dashboard')
            elif user_type == 'employee':
                messages.success(request, 'Welcome back, Employee!')
                return redirect('employee_view')
            else:
                messages.success(request, 'Welcome back!')
                return redirect('home')

        else:
            # Authentication failed — increment failed attempts for that user when profile exists
            if profile:
                profile.failed_login_attempts = profile.failed_login_attempts + 1
                if profile.failed_login_attempts >= getattr(settings, 'MAX_FAILED_LOGIN_ATTEMPTS', 5):
                    profile.lockout_until = timezone.now() + timedelta(minutes=getattr(settings, 'LOCKOUT_PERIOD_MINUTES', 15))
                profile.save(update_fields=['failed_login_attempts', 'lockout_until'])

            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'auth/login.html')


def two_factor_challenge(request):
    """Render and process the 2FA code / TOTP token verification flow.

    Expects session keys `pre_2fa_user_id` and `pre_2fa_method` to be set by `login_view` when 2FA is required.
    """
    user_id = request.session.get('pre_2fa_user_id')
    method = request.session.get('pre_2fa_method')
    otp_id = request.session.get('pre_2fa_otp_id')

    if not user_id or not method:
        messages.error(request, 'No 2FA authentication in progress.')
        return redirect('login')

    if request.method == 'POST':
        token = request.POST.get('token')
        if method in ('email', 'sms'):
            # verify OTP stored
            try:
                rec = OTP.objects.get(id=otp_id, user__id=user_id, used=False)
            except OTP.DoesNotExist:
                messages.error(request, 'Invalid or expired verification code.')
                return render(request, 'auth/two_factor.html', {'method': method})

            if rec.is_expired() or rec.code != token:
                messages.error(request, 'Invalid or expired verification code.')
                return render(request, 'auth/two_factor.html', {'method': method})

            # mark used and login
            rec.mark_used()
            user_obj = rec.user
            login(request, user_obj)
            # cleanup session
            request.session.pop('pre_2fa_user_id', None)
            request.session.pop('pre_2fa_otp_id', None)
            request.session.pop('pre_2fa_method', None)
            messages.success(request, 'Two-factor authentication successful.')
            return redirect('home')

        elif method == 'totp':
            token = request.POST.get('token')
            try:
                cu = CustomUser.objects.get(user__id=user_id)
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found for two-factor step.')
                return redirect('login')

            if not cu.totp_secret:
                messages.error(request, 'TOTP not configured for this account.')
                return redirect('login')

            # verify TOTP token
            ok = verify_totp(cu.totp_secret, token)
            if not ok:
                messages.error(request, 'Invalid authenticator code.')
                return render(request, 'auth/two_factor.html', {'method': method})

            # success — login
            login(request, cu.user)
            request.session.pop('pre_2fa_user_id', None)
            request.session.pop('pre_2fa_method', None)
            messages.success(request, 'Two-factor authentication successful.')
            return redirect('home')

    return render(request, 'auth/two_factor.html', {'method': method})


@login_required
def employee_view(request):
    # Only allow employees or admins
    try:
        user_profile = CustomUser.objects.get(user=request.user)
        user_type = user_profile.user_type
    except CustomUser.DoesNotExist:
        user_type = 'user'

    if user_type not in ('employee', 'admin'):
        messages.error(request, 'Access denied: Employee area.')
        return redirect('home')

    context = {
        'jobs_count': Job.objects.count(),
        'active_jobs_count': Job.objects.filter(is_active=True).count(),
        'quizzes_count': Quiz.objects.filter(is_active=True).count(),
        'courses_count': Course.objects.filter(is_active=True).count(),
        'latest_jobs': Job.objects.order_by('-posted_date')[:5],
        'latest_quizzes': Quiz.objects.order_by('-created_date')[:5],
    }
    return render(request, 'employee/dashboard.html', context)
