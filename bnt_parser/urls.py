from django.urls import path

from . import views

urlpatterns = [
    path("next-song/", views.NextSongView.as_view(), name="next-song"),
    path("submit-page/", views.SubmitPageView.as_view(), name="submit-page"),
]
