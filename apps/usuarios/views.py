from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import LoginForm

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {user.get_full_name()}')
                return redirect('dashboard')
            else:
                messages.error(request, 'Credenciales inválidas')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def perfil(request):
    return render(request, 'usuarios/perfil.html', {'usuario': request.user})

@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña cambiada exitosamente')
            return redirect('usuarios:perfil')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'usuarios/cambiar_password.html', {'form': form})