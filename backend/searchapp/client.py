from opensearchpy import OpenSearch
from django.conf import settings

def get_client():
    cfg = settings.OPENSEARCH
    auth = (cfg["USER"], cfg["PASS"]) if cfg["USER"] else None
    return OpenSearch(
        cfg["URL"],
        http_auth=auth,
        verify_certs=False,
        ssl_show_warn=False,
        timeout=10,
    )
