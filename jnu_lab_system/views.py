from django.shortcuts import render
from django.http import HttpResponse

def bad_request(request, exception):
    """400 Bad Request 错误页面"""
    return render(request, 'errors/400.html', status=400)

def permission_denied(request, exception):
    """403 Forbidden 错误页面"""
    return render(request, 'errors/403.html', status=403)

def page_not_found(request, exception):
    """404 Not Found 错误页面"""
    return render(request, 'errors/404.html', status=404)

def server_error(request):
    """500 Internal Server Error 错误页面"""
    return render(request, 'errors/500.html', status=500)