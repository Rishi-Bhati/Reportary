from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.http import HttpRequest, HttpResponse

@never_cache
def base(request: HttpRequest) -> HttpResponse:
    """Render the base template."""
    return render(request, "base.html", {})