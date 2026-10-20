from django.shortcuts import render

# Create your views here.

def login(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    elif request.method == 'POST':
        return render(request, 'login.html', {"text": "Function yet to be implemented"})