from django.conf.urls import url

from . import views

# Author: AHDS
# Creation date: 2016-06-23
# Modified by: MAP
# Last modified date:

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^login', views.login, name='login'),
    url(r'^logout_view', views.logout_view, name='logout_view'),
]
