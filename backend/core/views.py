from django.http import JsonResponse

def healthz(request):
    # Keep it DB-free to avoid masking boot errors
    return JsonResponse({"status": "ok", "service": "vendora"})
