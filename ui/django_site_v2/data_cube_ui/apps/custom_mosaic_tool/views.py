from django.shortcuts import render
from django.template import loader, RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

import json
from datetime import datetime, timedelta

from .models import Satellite, SatelliteBand, ResultType, Result, Query, Metadata, Area
from .forms import DataSelectForm, GeospatialForm
from .tasks import create_cloudfree_mosaic

from .utils import create_query_from_post

from collections import OrderedDict

# Author: AHDS
# Creation date: 2016-06-23
# Modified by: MAP
# Last modified date: 

# Loads the custom mosaic tool page. Includes the relevant forms/satellites, as well as running queries for the user.
# A form is created for each satellite based on the db contents for any given satellite.
@login_required
def custom_mosaic_tool(request, area_id):
    user_id = 0
    if request.user.is_authenticated():
        user_id = request.user.username
    satellites = Satellite.objects.all().order_by('satellite_id')
    forms = {}
    for satellite in satellites:
        bands = SatelliteBand.objects.filter(
            satellite_id=satellite.satellite_id).order_by('band_number')
        result_types = ResultType.objects.filter(
            satellite_id=satellite.satellite_id)
        results_list = [(result.result_id, result.result_type)
                        for result in result_types]
        bands_list = [(band.band_number, band.band_name) for band in bands]
        forms[satellite.satellite_id] = {'Data Selection': DataSelectForm(
            result_list=results_list, band_list=bands_list, auto_id=satellite.satellite_id + "_%s"), 'Geospatial Bounds': GeospatialForm(auto_id=satellite.satellite_id + "_%s")}
        # gets a flat list of the bands/result types and populates the choices.
    # will later be populated after we have authentication working.
    running_queries = Query.objects.filter(user_id=user_id, area_id=area_id, complete=False)

    area = Area.objects.get(area_id=area_id)

    context = {
        'satellites': satellites,
        'forms': forms,
        'running_queries': running_queries,
        'area': area
    }

    return render(request, 'map_tool.html', context)


# Submit a new request using post data.
# A query model is created with the relevant information and user id, then the data task is started.
# The response is a json obj. containing the query id.
@login_required
def submit_new_request(request):
    user_id = 0
    if request.user.is_authenticated():
        user_id = request.user.username
    if request.method == 'POST':
        response = {}
        response['msg'] = "OK"
        try:
            query_id = create_query_from_post(user_id, request.POST)
            create_cloudfree_mosaic.delay(query_id, user_id)
            response['request_id'] = query_id
        except:
            response['msg'] = "ERROR"
        return JsonResponse(response)
    else:
        return JsonResponse({'msg': "ERROR"})

# submit a new requset for a single scene from an existing query.
# clones the existing query and updates the date fields for a single day.
@login_required
def submit_new_single_request(request):
    user_id = 0
    if request.user.is_authenticated():
        user_id = request.user.username
    if request.method == 'POST':
        response = {}
        response['msg'] = "OK"
        try:
            #Get the query that this is a derivation of, clone it by setting pk to none.
            query = Query.objects.filter(query_id=request.POST['query_id'], user_id=user_id)[0]
            query.pk = None
            query.time_start = datetime.strptime(request.POST['date'], '%m/%d/%Y')
            query.time_end = query.time_start + timedelta(days=1)
            query.complete = False
            query.title = "Single acquision for " + request.POST['date']
            query.query_id = query.generate_query_id()
            query.save();
            create_cloudfree_mosaic.delay(query.query_id, user_id)
            response['request_id'] = query.query_id
        except:
            response['msg'] = "ERROR"
        return JsonResponse(response)
    else:
        return JsonResponse({'msg': "ERROR"})

# Cancel a running task by id.
# post data includes a query id to be cancelled. The result model is obtained,
# and if it is still running then the job is cancelled. If it is too late, then
# the job will proceed until completion.
@login_required
def cancel_request(request):
    user_id = 0
    if request.user.is_authenticated():
        user_id = request.user.username
    if request.method == 'POST':
        response = {}
        response['msg'] = "OK"
        try:
            query = Query.objects.get(query_id=request.POST['query_id'], user_id=user_id)
            result = Result.objects.get(query_id=request.POST['query_id'])
            if result.status == "WAIT" and query.complete == False:
                result.status = "CANCEL"
                result.save()
        except:
            response['msg'] = "ERROR"
        return JsonResponse(response)
    else:
        return JsonResponse({'msg': "ERROR"})


# gets a result by its query id.
# If the result does not yet exist in the db or there are no errors or "ok" signals, wait.
# if the result has errored in some way, all offending models are removed.
# if the result returns ok, then post a result.
# response is a json obj containing a msg and result. the result can either be the data
# or an obj containing the total scenes/progress.
@login_required
def get_result(request):
    if request.method == 'POST':
        response = {}
        try:
            result = Result.objects.get(query_id=request.POST['query_id'])
        except Result.DoesNotExist:
            result = None
            response['msg'] = "WAIT"
        except:
            result = None
            response['msg'] = "ERROR"
        if result:
            if result.status == "ERROR":
                response['msg'] = "ERROR"
                response['error_msg'] = result.result_path
                # get rid of the offending results, queries, metadatas.
                Query.objects.filter(query_id=result.query_id).delete()
                Metadata.objects.filter(query_id=result.query_id).delete()
                result.delete()
            elif result.status == "OK":
                response['msg'] = "OK"
                response['result'] = {'data': result.data_path, 'result': result.result_path, 'result_filled': result.result_filled_path, 'min_lat': result.latitude_min, 'max_lat': result.latitude_max,
                                      'min_lon': result.longitude_min, 'max_lon': result.longitude_max, 'total_scenes': result.total_scenes, 'scenes_processed': result.scenes_processed}
                # since there is a result, update all the currently running identical queries with complete=true;
                Query.objects.filter(query_id=result.query_id).update(complete=True)
            else:
                response['msg'] = "WAIT"
                response['result'] = {
                    'total_scenes': result.total_scenes, 'scenes_processed': result.scenes_processed}
        return JsonResponse(response)
    return JsonResponse({'msg': "ERROR"})


# gets a formatted view displaying a user's task history. Used in the custom mosaic tool view.
# no post data required. The user's authentication provides username, returns a view w/
# context including the last n query objects.
@login_required
def get_query_history(request, area_id):
    user_id = 0
    if request.user.is_authenticated():
        user_id = request.user.username
    history = Query.objects.filter(
        user_id=user_id, area_id=area_id).order_by('-query_start')[:10]
    context = {
        'query_history': history,
    }
    return render(request, 'query_history.html', context)


# Abstracted function to take any model.  Uses the class name as the key and
# builds a list of headers to go along with it.
def build_headers_dictionary(model):
    # List of attributes to filter out.  Note that these should match the attributes of the
    # class being passed in.
    exclusion_list = ['query_id', 'user_id', 'product_type', 'description']

    headers = list()
    headers_dictionary = OrderedDict()
    for field in model._meta.get_fields():
        header = str(field).rsplit('.', 1)[-1]
        if not any(header == exclusion for exclusion in exclusion_list):
            headers.append(header)

    headers_dictionary[model.__class__.__name__] = headers

    return headers_dictionary


# Quick method for formatting headers.
def format_headers(unformatted_dict):
    # Split and title the headers_dicionary for better display.
    formatted_headers = list()

    for field in unformatted_dict['Query']:
        formatted_headers.append(field.replace('_', " ").title())

    return formatted_headers


# View method for returning and rendering the HTML for the task manager.
@login_required
def get_task_manager(request):
    # Lists to be returned to the html for display.
    headers_dictionary = OrderedDict()
    data_dictionary = OrderedDict()

    headers_dictionary = build_headers_dictionary(Query())

    # Loop over all the Queries, get associated Metadata and Result.
    # Loop over all headers for each object and get data.  Then store in list and
    # add to dictionary to be returned to HTML.
    for query in Query.objects.all().order_by('-query_start')[:100]:
        data = list()
        for v in headers_dictionary['Query']:
            data.append(str(query.__dict__[v]))
        data_dictionary[query] = data

    formatted_headers_dictionary = OrderedDict()
    formatted_headers_dictionary['Query'] = format_headers(headers_dictionary)

    # Context being built up.
    context = {
        'data_dictionary': data_dictionary,  # Data to match headerss.
        # Formatted headers for easier viewing.
        'formatted_headers_dictionary': formatted_headers_dictionary,
    }

    return render(request, 'task_manager.html', context)


# Returns the rendered html with appropriate data for a Query and its Metadata and Results.
# Requires an ID to be passed from the previous page.
@login_required
def get_query_details(request, requested_query_id):
    query = Query.objects.get(id=requested_query_id)
    metadata = Metadata.objects.get(query_id=query.query_id)
    result = Result.objects.get(query_id=query.query_id)

    context = {
        'query': query,
        'metadata': metadata,
        'result': result,
    }

    return render(request, 'query_details.html', context)


# loads the results list from a list of query ids.
# Error handling: N/a. getlist always returns a list, so even if its a bad request
# itll return an empty list of queries and metadatas.
@login_required
def get_results_list(request, area_id):
    if request.method == 'POST':
        query_ids = request.POST.getlist('query_ids[]')
        queries = []
        metadata_entries = []
        for query_id in query_ids:
            queries.append(Query.objects.filter(query_id=query_id)[0])
            metadata_entries.append(
                Metadata.objects.filter(query_id=query_id)[0])

        context = {
            'queries': queries,
            'metadata_entries': metadata_entries
        }
        return render(request, 'results_list.html', context)
    return HttpResponse("Invalid Request.")

# TODO: some small description.
@login_required
def get_output_list(request, area_id):
    if request.method == 'POST':
        query_ids = request.POST.getlist('query_ids[]')
        #queries = []
        #metadata_entries = []
        data = {}
        for query_id in query_ids:
            # queries.append(Query.objects.filter(query_id=query_id)[0])
            # metadata_entries.append(Metadata.objects.filter(query_id=query_id)[0])
            data[Query.objects.filter(query_id=query_id)[0]] = Metadata.objects.filter(
                query_id=query_id)[0]

        context = {
            #'queries': queries,
            #'metadata_entries': metadata_entries
            'data': data
        }
        return render(request, 'output_list.html', context)
    return HttpResponse("Invalid Request.")
