from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from .forms import UserRegisterForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def home(request):
    return render(request, 'users/home.html')


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Hi {username}, your account was created successfully')
            return redirect('home')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required()
def profile(request):
    return render(request, 'users/profile.html')

def profilemanage(request):
    # Your view logic here
    return render(request, 'users/profilemanage.html')

def aboutus(request):
    # Your logic to gather data, if any
    return render(request, 'users/aboutus.html')

def live_stream(request):
    return render(request, 'users/live_stream.html')

def error_404(request,exception):
        return render(request, 'users/404.html' , status=404)