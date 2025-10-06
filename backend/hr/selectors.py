from django.db.models import QuerySet

def all_qs(model) -> QuerySet:
    qs = model.objects
    if hasattr(model, "is_deleted"):
        return qs.filter(is_deleted=False)
    return qs.all()
