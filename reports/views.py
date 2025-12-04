from django.shortcuts import render


# Create your views here.


def report_list(request):
    return render(request, 'report_list.html')

def report_detail(request, pk):
    return render(request, 'report_detail.html')

def create_report(request, pk):
    user = request.user
    return render(request, 'create_report.html')
