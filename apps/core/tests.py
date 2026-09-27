import json
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from graphene_django.utils.testing import GraphQLTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AppUser
from apps.bookings.models import Booking
from apps.bookings.services import cancel_booking, confirm_booking
from apps.destinations.models import Destination
from apps.guides.models import Guide
from apps.notifications.models import DeviceToken
from apps.payments.models import Payment
from apps.reviews.models import Review


def _auth(user):
    return {'AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


def _destination(**extra):
    values = dict(name='Assinie', description='Plage', location="Côte d'Ivoire",
                  price=100.0, category='Beach')
    values.update(extra)
    return Destination.objects.create(**values)


def _booking(user, destination, days_ahead=30, status=Booking.STATUS_PENDING, reference='AK-1'):
    check_in = timezone.localdate() + timedelta(days=days_ahead)
    return Booking.objects.create(
        user=user, reference=reference, destination_id=str(destination.pk),
        destination_name=destination.name, check_in_date=check_in,
        check_out_date=check_in + timedelta(days=2), guests=1, nights=2,
        total_price=229.0, status=status)


class PlatformEndpointsTest(TestCase):
    def test_health_check(self):
        response = Client().get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_legal_pages_in_three_languages(self):
        for document in ('privacy', 'terms'):
            for language in ('fr', 'en', 'de'):
                response = Client().get(f'/legal/{document}/?lang={language}')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'lang="{language}"')
        self.assertEqual(Client().get('/legal/unknown/').status_code, 404)


class AppSettingsTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    @override_settings(SUPPORT_WHATSAPP='2250700000000', STRIPE_SECRET_KEY='',
                       FREE_CANCELLATION_DAYS=7)
    def test_app_settings(self):
        data = json.loads(self.query(
            '{ appSettings(language: "de") { supportWhatsapp serviceFeeEur '
            'freeCancellationDays paymentsEnabled termsUrl } }').content)['data']['appSettings']
        self.assertEqual(data['supportWhatsapp'], '2250700000000')
        self.assertEqual(data['freeCancellationDays'], 7)
        self.assertFalse(data['paymentsEnabled'])
        self.assertTrue(data['termsUrl'].endswith('/legal/terms/?lang=de'))


class BookingLifecycleTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(
            email='traveller@example.com', password='pass1234!', language='en')
        self.destination = _destination()

    def test_new_booking_sends_request_received_email(self):
        self.query(
            'mutation($b: [BookingInputType]!) { upsertBookings(bookings: $b) { ok } }',
            variables={'b': [{
                'id': 'x', 'reference': 'AK-NEW', 'destinationId': str(self.destination.pk),
                'destinationName': 'x', 'checkInDate': '2030-01-10',
                'checkOutDate': '2030-01-12', 'guests': 1}]},
            headers=_auth(self.user))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Booking request received', mail.outbox[0].subject)

    def test_confirmation_emails_the_traveller(self):
        booking = _booking(self.user, self.destination)
        self.assertTrue(confirm_booking(booking))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_CONFIRMED)
        self.assertIn('Booking confirmed', mail.outbox[-1].subject)

    @mock.patch('apps.payments.services.refund_booking', return_value=True)
    def test_cancel_in_time_is_refunded(self, refund):
        _booking(self.user, self.destination, days_ahead=30)
        content = json.loads(self.query(
            'mutation { cancelBooking(reference: "AK-1") { ok refunded } }',
            headers=_auth(self.user)).content)
        self.assertTrue(content['data']['cancelBooking']['refunded'])
        refund.assert_called_once()

    @mock.patch('apps.payments.services.refund_booking', return_value=True)
    def test_late_cancellation_is_not_refunded(self, refund):
        booking = _booking(self.user, self.destination, days_ahead=2)
        self.assertFalse(cancel_booking(booking))
        refund.assert_not_called()
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_CANCELLED)


class PaymentsTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(email='payer@example.com', password='x')
        self.booking = _booking(self.user, _destination())

    @override_settings(STRIPE_SECRET_KEY='', STRIPE_PUBLISHABLE_KEY='')
    def test_payment_needs_stripe_configuration(self):
        content = json.loads(self.query(
            'mutation { createBookingPayment(reference: "AK-1") { clientSecret } }',
            headers=_auth(self.user)).content)
        self.assertIn('not available', content['errors'][0]['message'])

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    def test_webhook_rejects_unsigned_events(self):
        response = Client().post('/payments/stripe/webhook/', data='{}',
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    def test_successful_payment_confirms_the_booking(self):
        Payment.objects.create(booking=self.booking, stripe_payment_intent_id='pi_1',
                               amount=22900)
        event = {'type': 'payment_intent.succeeded', 'data': {'object': {'id': 'pi_1'}}}
        with mock.patch('stripe.Webhook.construct_event', return_value=event):
            response = Client().post('/payments/stripe/webhook/', data='{}',
                                     content_type='application/json',
                                     HTTP_STRIPE_SIGNATURE='t=1,v1=x')
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_CONFIRMED)
        self.assertEqual(Payment.objects.get().status, Payment.STATUS_SUCCEEDED)


class ReviewsAndGuidesTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'
    SUBMIT = ('mutation($d: ID!) { submitReview(destinationId: $d, rating: 4, '
              'comment: "Superbe") { rating authorName } }')

    def setUp(self):
        self.user = AppUser.objects.create_user(
            email='reviewer@example.com', password='x', display_name='Anna Schmidt')
        self.destination = _destination()

    def test_only_confirmed_travellers_can_review(self):
        denied = json.loads(self.query(self.SUBMIT, variables={'d': self.destination.pk},
                                       headers=_auth(self.user)).content)
        self.assertIn('errors', denied)
        _booking(self.user, self.destination, status=Booking.STATUS_CONFIRMED)
        allowed = json.loads(self.query(self.SUBMIT, variables={'d': self.destination.pk},
                                        headers=_auth(self.user)).content)
        self.assertEqual(allowed['data']['submitReview']['authorName'], 'Anna')
        self.destination.refresh_from_db()
        self.assertEqual((self.destination.rating, self.destination.review_count), (4.0, 1))

    def test_guides_for_a_destination(self):
        guide = Guide.objects.create(name='Koffi', languages=['fr', 'en'],
                                     whatsapp='2250700000001')
        guide.destinations.add(self.destination)
        Guide.objects.create(name='Inactive', is_active=False)
        data = json.loads(self.query(
            '{ guides(destinationId: %d) { name languages whatsapp } }'
            % self.destination.pk).content)['data']['guides']
        self.assertEqual(data, [{'name': 'Koffi', 'languages': ['fr', 'en'],
                                 'whatsapp': '2250700000001'}])


class AccountAndDevicesTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(email='gdpr@example.com', password='pass1234!')

    def test_delete_account_keeps_bookings_unlinked(self):
        booking = _booking(self.user, _destination())
        booking.notes = 'Allergic to peanuts'
        booking.save()
        wrong = json.loads(self.query(
            'mutation { deleteAccount(password: "nope") { ok } }',
            headers=_auth(self.user)).content)
        self.assertIn('errors', wrong)
        self.query('mutation { deleteAccount(password: "pass1234!") { ok } }',
                   headers=_auth(self.user))
        self.assertFalse(AppUser.objects.filter(email='gdpr@example.com').exists())
        booking.refresh_from_db()
        self.assertIsNone(booking.user)
        self.assertEqual(booking.notes, '')

    def test_preferences_and_device_registration(self):
        self.query('mutation { updatePreferences(language: "de") { ok } }',
                   headers=_auth(self.user))
        self.query('mutation { registerDevice(token: "fcm-1", platform: "android") { ok } }',
                   headers=_auth(self.user))
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'de')
        self.assertTrue(DeviceToken.objects.filter(user=self.user, token='fcm-1').exists())

    def test_trip_reminders_are_sent_once(self):
        destination = _destination()
        _booking(self.user, destination, days_ahead=1, status=Booking.STATUS_CONFIRMED)
        with mock.patch('apps.notifications.management.commands.'
                        'send_trip_reminders.notify_booking') as notify:
            call_command('send_trip_reminders', stdout=mock.Mock())
            call_command('send_trip_reminders', stdout=mock.Mock())
        notify.assert_called_once()


class DeploymentTests(TestCase):
    @override_settings(ALLOWED_HOSTS=['api.example.com'], SECURE_SSL_REDIRECT=True)
    def test_health_check_answers_probes_by_ip_over_http(self):
        # Render and Docker probe the container directly, not via the domain.
        response = Client().get('/healthz/', HTTP_HOST='10.0.0.7:10000')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    @override_settings(ALLOWED_HOSTS=['api.example.com'])
    def test_other_paths_still_validate_the_host(self):
        response = Client().get('/legal/terms/', HTTP_HOST='evil.example.com')
        self.assertEqual(response.status_code, 400)

    def test_object_storage_urls_are_kept_as_they_are(self):
        from apps.destinations.models import public_url

        stored = mock.Mock(url='https://media.example.com/media/2026/09/a.jpg')
        self.assertEqual(public_url(stored), 'https://media.example.com/media/2026/09/a.jpg')
        on_disk = mock.Mock(url='/media/2026/09/a.jpg')
        with override_settings(PUBLIC_BASE_URL='https://api.example.com/'):
            self.assertEqual(public_url(on_disk), 'https://api.example.com/media/2026/09/a.jpg')

    def test_media_bucket_settings_give_public_urls(self):
        # Fresh interpreter: storage settings are read once at start-up.
        import os
        import subprocess
        import sys

        env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings', 'DEBUG': 'True',
               'MEDIA_BUCKET': 'akwaba-media',
               'MEDIA_ENDPOINT_URL': 'https://account.r2.cloudflarestorage.com',
               'MEDIA_PUBLIC_DOMAIN': 'media.example.com',
               'MEDIA_ACCESS_KEY_ID': 'id', 'MEDIA_SECRET_ACCESS_KEY': 'secret'}
        script = ('import django; django.setup()\n'
                  'from django.core.files.storage import default_storage as s\n'
                  'print(s.url("media/2026/09/a.jpg"))')
        output = subprocess.run([sys.executable, '-c', script], env=env, check=True,
                                capture_output=True, text=True).stdout.strip()
        # Disk storage would give /media/...: the bucket's public domain is used.
        self.assertEqual(output, 'https://media.example.com/media/2026/09/a.jpg')
