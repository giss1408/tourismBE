import json
from graphene_django.utils.testing import GraphQLTestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import AppUser
from apps.destinations.models import Destination

from .models import Booking


def _auth_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'AUTHORIZATION': f'Bearer {token}'}


class BookingQueryTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(
            email='booker@example.com',
            password='pass1234!',
        )
        self.booking = Booking.objects.create(
            user=self.user,
            reference='EW-001',
            destination_id='d1',
            destination_name='Paris',
            check_in_date='2026-09-01',
            check_out_date='2026-09-05',
            guests=2,
            nights=4,
            total_price=1200.0,
            status='Confirmed',
        )

    def test_fetch_bookings_authenticated(self):
        response = self.query(
            '''
            { bookings { id reference destinationName status } }
            ''',
            headers=_auth_header(self.user),
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['bookings']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['reference'], 'EW-001')

    def test_fetch_bookings_unauthenticated_raises_error(self):
        response = self.query('{ bookings { id } }')
        content = json.loads(response.content)
        self.assertIn('errors', content)


class UpsertBookingsMutationTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(
            email='upsert@example.com',
            password='pass1234!',
        )
        self.destination = Destination.objects.create(
            name='Grand-Bassam', description='Plage', location='Côte d\'Ivoire',
            price=100.0, discount=0.1, category='Beach')

    def test_upsert_creates_booking(self):
        response = self.query(
            '''
            mutation {
              upsertBookings(bookings: [{
                id: "client-1"
                reference: "EW-2026-999"
                destinationId: "%s"
                destinationName: "Bali"
                checkInDate: "2026-10-01"
                checkOutDate: "2026-10-07"
                guests: 1
                nights: 6
                totalPrice: 850.0
                status: "Confirmed"
              }]) {
                ok
              }
            }
            ''' % self.destination.pk,
            headers=_auth_header(self.user),
        )
        self.assertResponseNoErrors(response)
        booking = Booking.objects.get(reference='EW-2026-999', user=self.user)
        # Price and status are decided by the server, not the app:
        # 6 nights x 1 guest x 100 with a 10% discount, plus the 29 fee.
        self.assertEqual(booking.total_price, 569.0)
        self.assertEqual(booking.status, Booking.STATUS_PENDING)
        self.assertEqual(booking.destination_name, 'Grand-Bassam')

    def _upsert(self, reference, status, destination_id=None):
        return self.query(
            '''
            mutation($b: [BookingInputType]!) { upsertBookings(bookings: $b) { ok } }
            ''',
            variables={'b': [{
                'id': reference, 'reference': reference,
                'destinationId': destination_id or str(self.destination.pk),
                'destinationName': 'x', 'checkInDate': '2026-10-01',
                'checkOutDate': '2026-10-03', 'guests': 2, 'status': status,
            }]},
            headers=_auth_header(self.user),
        )

    def test_app_can_cancel_but_not_confirm(self):
        self.assertResponseNoErrors(self._upsert('R-1', 'Pending'))
        self._upsert('R-1', 'Confirmed')
        self.assertEqual(Booking.objects.get(reference='R-1').status, 'Pending')
        self._upsert('R-1', 'Cancelled')
        self.assertEqual(Booking.objects.get(reference='R-1').status, 'Cancelled')
        self._upsert('R-1', 'Pending')
        self.assertEqual(Booking.objects.get(reference='R-1').status, 'Cancelled')

    def test_unknown_destination_is_rejected(self):
        response = self._upsert('R-2', 'Pending', destination_id='999999')
        self.assertIn('errors', json.loads(response.content))
        self.assertFalse(Booking.objects.filter(reference='R-2').exists())

    def test_upsert_unauthenticated_raises_error(self):
        response = self.query(
            '''
            mutation {
              upsertBookings(bookings: [{
                id: "c1"
                reference: "R1"
                destinationId: "d1"
                destinationName: "N"
                checkInDate: "2026-10-01"
                checkOutDate: "2026-10-02"
              }]) { ok }
            }
            '''
        )
        content = json.loads(response.content)
        self.assertIn('errors', content)
