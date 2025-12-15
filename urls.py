from django.urls import path
from . import views

urlpatterns = [
    # ...existing code...
    path('admin_panel/regions', views.regions_view, name='regions_view'),
    path('admin_panel/regions/update', views.update_region, name='update_region'),
    path('admin_panel/regions/delete', views.delete_region, name='delete_region'),
    path('admin_panel/regions/add', views.add_region, name='add_region'),
]