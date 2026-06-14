from django.urls import path

from . import views

urlpatterns = [
    path("word/", views.WordSearchView.as_view(), name="word-search"),
    path("writers/", views.WriterListView.as_view(), name="writer-list"),
]
