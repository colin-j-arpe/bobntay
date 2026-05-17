from django.urls import path

from . import views

urlpatterns = [
    path('word/', views.WordSearchView.as_view(), name='word-search'),
]
