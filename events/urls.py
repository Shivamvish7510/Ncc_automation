
from django.urls import path
from . import views

urlpatterns = [
    # IMPORTANT: More specific URLs MUST come BEFORE generic ones
    
    # Create must come before <slug> detail
    path('create/', views.event_create, name='event_create'),
    
    # My events (cadet specific)
    path('my-events/', views.cadet_events_view, name='cadet_events'),
    
    # Registration actions (before slug)
    path('register/<slug:slug>/', views.event_register, name='event_register'),
    path('cancel/<int:registration_id>/', views.event_cancel_registration, name='event_cancel_registration'),
    
    # Resource delete (before slug)
    path('resources/<int:resource_id>/delete/', views.event_delete_resources, name='event_delete_resources'),
    
    # List view (root)
    path('', views.event_list, name='event_list'),
    
    # Detail view with slug (AFTER all specific URLs)
    path('<slug:slug>/', views.event_detail, name='event_detail'),
    
    # Update and delete (after detail)
    path('<slug:slug>/update/', views.event_update, name='event_update'),
    path('<slug:slug>/delete/', views.event_delete, name='event_delete'),
    
    # Management views
    path('<slug:slug>/registrations/', views.event_registrations, name='event_registrations'),
    path('<slug:slug>/participation/', views.event_manage_participation, name='event_manage_participation'),
    path('<slug:slug>/resources/', views.event_manage_resources, name='event_manage_resources'),
    path('<slug:slug>/announcements/', views.event_announcements, name='event_announcements'),
]
