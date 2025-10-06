from opensearchpy import OpenSearch
import os

def get_opensearch_client():
    host = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
    user = os.getenv("OPENSEARCH_USER", "admin")
    password = os.getenv("OPENSEARCH_PASS", "admin")

    client = OpenSearch(
        hosts=[host],
        http_auth=(user, password),
        use_ssl=host.startswith("https"),
        verify_certs=False,
        ssl_show_warn=False,
    )
    return client
