from django.urls import path
from .views import data_visualization_views

urlpatterns = [
    path('data_visualization/get', data_visualization_views.get),
]
