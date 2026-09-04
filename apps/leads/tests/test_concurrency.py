import threading

from django.db import connection
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.clients.models import Client
from apps.leads import services as lead_services
from apps.leads.models import Lead
from apps.professionals.models import Professional


class LeadConversionConcurrencyTests(TransactionTestCase):
    """Prova que o select_for_update em convert_to_client (apps/leads/services.py)
    realmente impede duas conversoes simultaneas do mesmo lead criarem 2 Clients.
    Usa TransactionTestCase (nao TestCase) porque precisa de transacoes/conexoes
    de verdade pra o lock entre threads fazer sentido."""

    def test_two_simultaneous_converts_create_only_one_client(self):
        therapist = User.objects.create(firebase_uid="ther-x", email="x@teste.com", role=User.THERAPIST)
        professional = Professional.objects.create(user=therapist, slug="terapeuta-x", full_name="X")
        lead = Lead.objects.create(professional=professional, name="Lead X", email="x@teste.com")

        errors = []

        def attempt_convert():
            try:
                lead_services.convert_to_client(therapist, lead)
            except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha da thread
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt_convert) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(Client.objects.filter(lead=lead).count(), 1)
        self.assertEqual(len(errors), 1)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.CONVERTED)
