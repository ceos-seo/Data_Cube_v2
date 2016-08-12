from django.conf.urls import url

from . import views

# Author: AHDS
# Creation date: 2016-06-23
# Modified by:
# Last modified date:

urlpatterns = [
    url(r'^submit$', views.submit_new_request, name='submit_new_request'),
    url(r'^submit_single$', views.submit_new_single_request, name='submit_new_single_request'),
    url(r'^cancel$', views.cancel_request, name='cancel_request'),
    url(r'^result$', views.get_result, name='get_result'),
    url(r'^(?P<area_id>[\w\-]+)/query_history$', views.get_query_history, name='get_query_history'),
    url(r'^(?P<area_id>[\w\-]+)/results_list$', views.get_results_list, name='get_results_list'),
    url(r'^(?P<area_id>[\w\-]+)/output_list$', views.get_output_list, name='get_output_list'),
    url(r'^task_manager/$', views.get_task_manager, name='get_task_manager'),
    url(r'^task_manager/details/(\d+)', views.get_query_details, name='get_query_details'),
    url(r'^(?P<area_id>[\w\-]+)/$', views.custom_mosaic_tool, name='custom_mosaic_tool')
]
