from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

class EventSmartFilter(BaseFilterBackend):
    """
    Supports query params:
      - name (comma-separated)
      - since, until (ISO datetime)
      - session_id, device_id, user_id
      - country (comma-separated)
      - contains (JSON-path-ish: key.eq=value; key.icontains=foo; key.exists=true)
    """
    def filter_queryset(self, request, queryset, view):
        q = Q()
        p = request.query_params

        if (names := p.get("name")):
            q &= Q(name__in=[n.strip() for n in names.split(",") if n.strip()])

        since = p.get("since")
        until = p.get("until")
        if since:
            q &= Q(ts__gte=since)
        if until:
            q &= Q(ts__lte=until)

        for field in ("session_id", "device_id", "user_id", "country"):
            if v := p.get(field):
                vals = [x.strip() for x in v.split(",") if x.strip()]
                q &= Q(**{f"{field}__in": vals})

        qs = queryset.filter(q)

        # Simple JSON contains operators
        contains = p.getlist("contains")
        for rule in contains:
            # examples: props.product_id.eq=123   props.category.icontains=phones   props.has_discount.exists=true
            try:
                left, value = rule.split("=", 1)
                key, op = left.rsplit(".", 1) if "." in left else (left, "eq")
                key = key.replace("props.", "", 1)
                if op == "eq":
                    qs = qs.filter(**{f"props__{key}": value})
                elif op == "icontains":
                    qs = qs.filter(**{f"props__{key}__icontains": value})
                elif op == "exists":
                    want = value.lower() in ("1", "true", "yes")
                    qs = qs.filter(**({f"props__has_key": key} if want else ~Q(**{f"props__has_key": key})))
            except Exception:
                continue

        return qs
