import sys
import json
import time
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

class Command(BaseCommand):
    help = "Run internal health checks (DB, cache, Celery) and print JSON summary for CI/CD pipelines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--db", action="store_true", help="Check database connectivity"
        )
        parser.add_argument(
            "--cache", action="store_true", help="Check cache connectivity"
        )
        parser.add_argument(
            "--celery", action="store_true", help="Check Celery connectivity (requires ping task)"
        )
        parser.add_argument(
            "--json", action="store_true", help="Output as JSON (default is pretty text)"
        )

    def handle(self, *args, **opts):
        checks = {
            "db": opts.get("db"),
            "cache": opts.get("cache"),
            "celery": opts.get("celery"),
        }

        results = {
            "time": timezone.now().isoformat(),
            "env": getattr(settings, "ENV", "dev"),
            "debug": bool(settings.DEBUG),
            "ok": True,
            "checks": {},
        }

        # --- DB check ---
        if checks["db"]:
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
                results["checks"]["db"] = {"ok": True}
            except Exception as e:
                results["checks"]["db"] = {"ok": False, "error": str(e)}
                results["ok"] = False

        # --- Cache check ---
        if checks["cache"]:
            try:
                key = "core_check_probe"
                val = str(time.time())
                cache.set(key, val, timeout=10)
                got = cache.get(key)
                if got == val:
                    results["checks"]["cache"] = {"ok": True}
                else:
                    results["checks"]["cache"] = {"ok": False, "error": "Cache mismatch"}
                    results["ok"] = False
            except Exception as e:
                results["checks"]["cache"] = {"ok": False, "error": str(e)}
                results["ok"] = False

        # --- Celery check ---
        if checks["celery"]:
            try:
                from aiapp.tasks import ping
                res = ping.delay()
                val = res.get(timeout=5)
                results["checks"]["celery"] = {"ok": val == "pong"}
                if val != "pong":
                    results["ok"] = False
            except Exception as e:
                results["checks"]["celery"] = {"ok": False, "error": str(e)}
                results["ok"] = False

        # --- Output formatting ---
        if opts.get("json"):
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.stdout.write(f"\n=== Vendora Core Health Check ({results['time']}) ===\n")
            self.stdout.write(f"Environment: {results['env']} | Debug={results['debug']}\n\n")
            for key, val in results["checks"].items():
                mark = "✅" if val.get("ok") else "❌"
                err = f" ({val.get('error')})" if not val.get("ok") else ""
                self.stdout.write(f" {mark}  {key.upper()}{err}\n")
            self.stdout.write(f"\nOverall: {'✅ OK' if results['ok'] else '❌ FAILED'}\n")

        # Exit with code 1 on failure (for CI)
        if not results["ok"]:
            sys.exit(1)
