from django.shortcuts import render, redirect
from django.template import loader, RequestContext
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpResponse, JsonResponse

# Author: AHDS
# Creation date: 2016-06-23
# Modified by: MAP
# Last modified date:

# Create your views here.
def home(request):
    context = {

    }
    return render(request, 'index.html', context)

def login(request):
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
    auth_logout(request)
    return redirect('home')
