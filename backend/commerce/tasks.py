from celery import shared_task
from django.core.cache import cache

@shared_task
def invalidate_product_cache_task(product_id):
    """
    Asynchronous task to invalidate cache for a product's detail and list views.
    """
    # Import locally to avoid circular dependencies during app startup
    from django.test import RequestFactory
    from django.urls import reverse
    from django.utils.cache import get_cache_key

    factory = RequestFactory()

    # Invalidate product detail view
    # Use reverse() to be more robust against URL changes
    detail_path = reverse("product-detail", kwargs={"pk": product_id})
    request_detail = factory.get(detail_path)
    key_detail_anon = get_cache_key(request_detail, headers={})
    key_detail_auth = get_cache_key(request_detail, headers={"HTTP_AUTHORIZATION": "dummy"})
    if key_detail_anon: cache.delete(key_detail_anon)
    if key_detail_auth: cache.delete(key_detail_auth)

    # Invalidate product list view
    list_path = reverse("product-list")
    request_list = factory.get(list_path)
    key_list_anon = get_cache_key(request_list, headers={})
    key_list_auth = get_cache_key(request_list, headers={"HTTP_AUTHORIZATION": "dummy"})
    if key_list_anon: cache.delete(key_list_anon)
    if key_list_auth: cache.delete(key_list_auth)