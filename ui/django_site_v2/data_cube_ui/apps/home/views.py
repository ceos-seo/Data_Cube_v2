# Copyright 2016 United States Government as represented by the Administrator
# of the National Aeronautics and Space Administration. All Rights Reserved.
#
# Portion of this code is Copyright Geoscience Australia, Licensed under the
# Apache License, Version 2.0 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of the License
# at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# The CEOS 2 platform is licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.shortcuts import render, redirect
from django.template import loader, RequestContext
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpResponse, JsonResponse

"""
Contains all the views for the Home application.
"""

# Author: AHDS
# Creation date: 2016-06-23
# Modified by: MAP
# Last modified date:

def home(request):
    """
    Navigates to the home page of the application.

    **Context**

    **Template**

    :template:`home/index.html`
    """

    context = {

    }
    return render(request, 'index.html', context)

def login(request):
    """
    Navigates to the login page of the application.  Note this is used as the POST for submitting
    a request to log in as well as the initial landing page.

    **Context**

    ``message``
        An error message in the event username and/or password is incorrect.
    ``next``
        The redirect page upon successfull login.

    **Template**

    :template:`home/login_page.html`
    """
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        next = request.POST.get('next', "/")
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                auth_login(request, user)
                # Redirect to a success page.
                return redirect(next)
            else:
                # Return a 'disabled account' error message
                ...
        else:
            # Return an 'invalid login' error message.
            context = {
                'message': "Please enter a correct username and password combination."
            }
            return render(request, 'login_page.html', context)
            ...
    else:
        context = {}
        if request.GET:
            next = request.GET['next']
            if request.user.is_authenticated():
                return redirect(next)
            context['next'] = next
        return render(request, 'login_page.html', context)

def logout_view(request):
    """
    Logout view that redirects the user to the home page.

    **Context**

    **Template**

    """
    auth_logout(request)
    return redirect('home')
