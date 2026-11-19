from django.http import HttpResponse


def devtools_probe(request):
    return HttpResponse(status=204)
