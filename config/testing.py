from django.conf import settings
from django.core.management.base import CommandError
from django.test.runner import DiscoverRunner

_ALLOWED_TEST_HOSTS = {"localhost", "127.0.0.1", ""}


class SafeTestRunner(DiscoverRunner):
    """ponytail: trava simples contra rodar a suite de testes contra um
    Postgres remoto (ex.: Supabase) por engano — `manage.py test` faz
    CREATE DATABASE/DROP DATABASE, e um incidente real do QA mostrou que
    isso trava (ou pior, mexe) num banco de producao. Upgrade quando surgir
    um Postgres de CI dedicado: trocar por allowlist de host via env var."""

    def setup_databases(self, **kwargs):
        host = settings.DATABASES["default"].get("HOST", "")
        if host not in _ALLOWED_TEST_HOSTS:
            raise CommandError(
                f"DATABASE_URL aponta para um host remoto ({host!r}) - recusando rodar "
                "manage.py test contra ele. Rode com um Postgres local, ex.:\n\n"
                "  DATABASE_URL=postgresql://vivamente:vivamente@localhost:5432/vivamente "
                "python manage.py test\n"
            )
        return super().setup_databases(**kwargs)
