from typing import List, Dict, Any
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from .views import AiModelViewSet

factory = APIRequestFactory()

def recommend_content_django(model_id: str, tenant, recent: List[str], k: int = 12, exclude: List[str] = None) -> Dict[str, Any]:
    view = AiModelViewSet.as_view({"post": "recommend_content"})
    req = factory.post(reverse("aimodel-detail", args=[model_id]) + "recommend/content/",
                       {"recent": recent, "k": k, "exclude": exclude or []}, format="json")
    req.user = getattr(tenant, "owner", None)  # optional
    req.tenant = tenant
    return view(req, pk=model_id).data
