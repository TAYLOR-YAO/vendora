from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from commerce.models import Product
from crm.models import Contact
from support.models import Ticket
from .indexers import index_product, delete_product

@receiver(post_save, sender=Product)
def idx_product(sender, instance, **kw):
    if not instance.is_active:
        return
    index_product({
        "id": instance.id,
        "tenant": str(instance.tenant_id),
        "name": instance.name,
        "desc": instance.description or "",
        "price": float(instance.default_price or 0),
        "business": str(instance.business_id),
    })

@receiver(post_delete, sender=Product)
def del_product(sender, instance, **kw):
    delete_product(str(instance.id))
