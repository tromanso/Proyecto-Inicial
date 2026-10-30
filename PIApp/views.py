from django.shortcuts import render

# Create your views here.

def login(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    elif request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        contexto = {
            'mensaje': f'Intentaste ingresar con: {email}'
        }
        return render(request, 'login.html', contexto)