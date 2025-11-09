# views.py
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import InregistrareFormular, LoginFormular, ProfileForm
from .models import Profile


def _get_safe_redirect(request):
    """Return a sanitized `next` parameter if it is safe to use."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def register(request):
    if request.user.is_authenticated:
        return redirect("index")

    redirect_to = _get_safe_redirect(request)

    if request.method == "POST":
        form = InregistrareFormular(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Cont creat cu succes. Bine ai venit la UNITEX!")
            return redirect(redirect_to or "index")
    else:
        form = InregistrareFormular()

    return render(request, "accounts/signup.html", {"form": form, "redirect_to": redirect_to})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    redirect_to = _get_safe_redirect(request)

    if request.method == "POST":
        form = LoginFormular(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, "Te-ai autentificat cu succes.")
            return redirect(redirect_to or "index")
    else:
        form = LoginFormular()

    return render(request, "accounts/login.html", {"form": form, "redirect_to": redirect_to})


@login_required(login_url="login")
def logout(request):
    auth_logout(request)
    return redirect("login")


@login_required
def profile(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "accounts/profile.html", {"user_profile": user_profile})


@login_required
def edit_profile(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil actualizat cu succes.")
            return redirect("inregistrare_profile")
    else:
        form = ProfileForm(instance=user_profile)

    return render(request, "accounts/edit_profile.html", {"form": form})
