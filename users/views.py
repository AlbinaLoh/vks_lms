from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .forms import LoginForm

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_active:
                login(request, user)
                # Перенаправление по ролям
                if user.is_staff:
                    return redirect('/admin/')
                elif user.groups.filter(name='Teachers').exists():
                    return redirect('teacher_dashboard')
                elif user.groups.filter(name='Students').exists():
                    return redirect('student_dashboard')
                else:
                    return render(request, 'users/login.html', {'form': form, 'error': 'Роль не определена.'})
            else:
                return render(request, 'users/login.html', {'form': form, 'error': 'Неверные данные.'})
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})
