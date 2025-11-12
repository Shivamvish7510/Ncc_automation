from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles):
    """Decorator to restrict access based on user role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if request.user.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator for admin-only views"""
    return role_required(['ADMIN'])(view_func)


def officer_required(view_func):
    """Decorator for officer and admin views"""
    return role_required(['OFFICER', 'ADMIN'])(view_func)


def cadet_only(view_func):
    """Decorator for cadet-only views"""
    return role_required(['CADET'])(view_func)