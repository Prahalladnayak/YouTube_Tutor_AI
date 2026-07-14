# backend/views/auth_views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

def home(request):
    """Render the landing page"""
    return render(request, 'analyzer/home.html')

def about(request):
    """Render the about page"""
    return render(request, 'analyzer/about.html')

def login_view(request):
    """Handle user login"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Check for success message from signup
    signup_success = False
    for message in messages.get_messages(request):
        if 'success' in message.tags and 'Account created successfully' in message.message:
            signup_success = True
            break
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember')
        
        # Try to get user by email (username field in Django)
        try:
            user = User.objects.get(email=email)
            username = user.username
        except User.DoesNotExist:
            username = email  # Fallback to email as username
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login the user
            login(request, user)
            
            # Handle "remember me" option
            if not remember_me:
                # Set session to expire when browser closes
                request.session.set_expiry(0)
            
            # Get the 'next' parameter properly
            next_url = request.GET.get('next')
            if next_url:
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect(next_url)
            else:
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password. Please try again.')
    
    return render(request, 'analyzer/login.html', {
        'signup_success': signup_success
    })

def signup_view(request):
    """Handle user registration"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        terms = request.POST.get('terms')
        
        # Validation
        errors = []
        
        # Check if passwords match
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Check password strength
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')
        
        # Check if username (email) already exists
        if User.objects.filter(username=email).exists():
            errors.append('An account with this email already exists.')
        
        # Check terms agreement
        if not terms:
            errors.append('You must agree to the Terms of Service.')
        
        # If no errors, create user
        if not errors:
            try:
                # Create user with email as username
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )
                
                # Set first and last name if provided
                if full_name:
                    name_parts = full_name.split(' ', 1)
                    user.first_name = name_parts[0]
                    if len(name_parts) > 1:
                        user.last_name = name_parts[1]
                
                user.save()
                
                # Redirect to login with success message
                messages.success(request, f'Account created successfully! Welcome to GuideTube, {full_name or email}. Please log in to continue.')
                return redirect('login')
                
            except Exception as e:
                errors.append(f'Error creating account: {str(e)}')
        
        for error in errors:
            messages.error(request, error)
            
    return render(request, 'analyzer/signup.html')

@login_required
def dashboard_view(request):
    """Show user dashboard after login"""
    user_data = {
        'name': request.user.first_name or request.user.username,
        'email': request.user.email,
        'join_date': request.user.date_joined.strftime('%B %d, %Y') if request.user.date_joined else 'Recently'
    }
    
    return render(request, 'analyzer/dashboard.html', {
        'user': request.user,
        'user_data': user_data
    })

def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')
