from typing import Dict, Any
from .client import get_client

PRODUCT_INDEX = "products"
TICKET_INDEX = "tickets"
CONTACT_INDEX = "contacts"

def ensure_index(name: str, mappings: Dict[str, Any]):
    os = get_client()
    if not os.indices.exists(name):
        os.indices.create(name, body={"mappings": mappings})

def index_product(doc: Dict[str, Any]):
    os = get_client()
    ensure_index(PRODUCT_INDEX, {"properties": {"name": {"type":"text"}, "desc":{"type":"text"}, "tenant":{"type":"keyword"}}})
    os.index(PRODUCT_INDEX, id=str(doc["id"]), body=doc, refresh=True)

def delete_product(id_: str):
    os = get_client()
    os.delete(PRODUCT_INDEX, id=id_, ignore=[404], refresh=True)

# replicate for tickets/contacts as needed
