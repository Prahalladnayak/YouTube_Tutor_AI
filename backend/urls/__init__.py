# backend/urls/__init__.py
from django.urls import path
from backend.views import auth_views, video_views, comparison_views

urlpatterns = [
    # Public pages
    path('', auth_views.home, name='home'),
    path('about/', auth_views.about, name='about'),
    
    # Authentication
    path('login/', auth_views.login_view, name='login'),
    path('signup/', auth_views.signup_view, name='signup'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('dashboard/', auth_views.dashboard_view, name='dashboard'),
    
    # Protected pages (require login)
    path('analyze/', video_views.video_analyse_QA, name='video_analyse_QA'),
    path('compare/', comparison_views.compare_videos, name='compare'),
]
