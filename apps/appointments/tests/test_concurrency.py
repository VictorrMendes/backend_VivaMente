import threading
from datetime import timedelta

from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments import services
from apps.appointments.models import Appointment
from apps.appointments.serializers import AppointmentSelfWriteSerializer
from apps.clients.models import Client
from apps.professionals.models import Professional


class AppointmentOverlapConcurrencyTests(TransactionTestCase):
    """A checagem em services.py (_validate_no_overlap) e um SELECT antes do
    INSERT: sozinha tem uma janela de corrida. Quem garante de verdade e a
    ExclusionConstraint do Postgres (apps/appointments/models.py). Esse teste
    prova que 2 requests simultaneas pro mesmo horario resultam em 1
    agendamento so, nao 2."""

    def test_two_simultaneous_bookings_create_only_one_appointment(self):
        therapist = User.objects.create(firebase_uid="ther-x", email="x@teste.com", role=User.THERAPIST)
        professional = Professional.objects.create(user=therapist, slug="terapeuta-x", full_name="X")
        client = Client.objects.create(professional=professional, name="Cliente X")
        starts_at = timezone.now() + timedelta(days=1)
        ends_at = starts_at + timedelta(minutes=50)

        errors = []

        def attempt_booking():
            try:
                serializer = AppointmentSelfWriteSerializer(
                    data={
                        "client": client.id,
                        "starts_at": starts_at.isoformat(),
                        "ends_at": ends_at.isoformat(),
                    }
                )
                serializer.is_valid(raise_exception=True)
                services.create_appointment(therapist, serializer)
            except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha da thread
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt_booking) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(
            Appointment.objects.filter(professional=professional, starts_at=starts_at).count(), 1
        )
        self.assertEqual(len(errors), 1)
