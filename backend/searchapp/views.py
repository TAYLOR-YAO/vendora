from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .client import get_client
from .indexers import PRODUCT_INDEX, TICKET_INDEX, CONTACT_INDEX

class SearchView(APIView):
    """
    GET /api/v1/search/?q=phone&scope=product,ticket&tenant=...
    """
    def get(self, request):
        q = request.query_params.get("q") or ""
        scopes = (request.query_params.get("scope") or "product").split(",")
        tenant = request.query_params.get("tenant")
        os = get_client()

        def run(index):
            body = {"query": {"bool": {"must":[{"multi_match":{"query":q,"fields":["*"]}}],
                                          "filter": [{"term":{"tenant": tenant}}] if tenant else []}}}
            res = os.search(index=index, body=body)
            return [hit["_source"] | {"_id": hit["_id"], "_score": hit["_score"]} for hit in res["hits"]["hits"]]

        data = {}
        if "product" in scopes:
            data["product"] = run(PRODUCT_INDEX)
        if "ticket" in scopes:
            data["ticket"] = run(TICKET_INDEX)
        if "contact" in scopes:
            data["contact"] = run(CONTACT_INDEX)

        return Response(data, status=status.HTTP_200_OK)
