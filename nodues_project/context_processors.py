from django.conf import settings
from clearance.models import Notification

def global_project_context(request):
    """
    Context processor to inject university metadata, unread notification count,
    and user role helpers into every template context.
    """
    context = {
        'UNIVERSITY_NAME': getattr(settings, 'UNIVERSITY_NAME', 'National Institute of Technology & Science'),
        'UNIVERSITY_SHORT_NAME': getattr(settings, 'UNIVERSITY_SHORT_NAME', 'NITS'),
        'UNIVERSITY_SUBTITLE': getattr(settings, 'UNIVERSITY_SUBTITLE', 'University No Dues Clearance & Verification System'),
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }

    if request.user.is_authenticated:
        try:
            notifications_qs = Notification.objects.filter(recipient=request.user)
            context['unread_notifications_count'] = notifications_qs.filter(is_read=False).count()
            context['recent_notifications'] = notifications_qs[:5]
        except Exception:
            pass

    return context
