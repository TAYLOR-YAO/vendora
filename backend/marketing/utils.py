from typing import Iterable, Tuple
from django.db.models import Q, QuerySet
from crm.models import Customer

# VERY simple rule engine for your segment DSL
# Supports ops: eq, ne, lt, lte, gt, gte, contains, in, isnull (with True/False)
OP_MAP = {
    "eq": "",
    "ne": "",
    "lt": "__lt",
    "lte": "__lte",
    "gt": "__gt",
    "gte": "__gte",
    "contains": "__icontains",
    "in": "__in",
    "isnull": "__isnull",
}

def build_q(rule) -> Q:
    field = rule.get("field")
    op = rule.get("op", "eq")
    value = rule.get("value")
    if op not in OP_MAP:
        return Q()  # ignore unknown
    suffix = OP_MAP[op]
    lookup = f"{field}{suffix}"
    if op == "ne":
        return ~Q(**{field: value})
    return Q(**{lookup: value})

def resolve_segment_queryset(tenant, definition: dict) -> QuerySet:
    qs = Customer.objects.filter(tenant=tenant)
    if not definition:
        return qs

    # Combine "all" (AND) and/or "any" (OR) blocks
    cond = Q()
    all_rules = definition.get("all")
    any_rules = definition.get("any")
    if all_rules:
        conj = Q()
        for r in all_rules:
            conj &= build_q(r)
        cond &= conj
    if any_rules:
        disj = Q()
        for r in any_rules:
            disj |= build_q(r)
        cond &= disj
    return qs.filter(cond)
