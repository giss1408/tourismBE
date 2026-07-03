import json
from graphene_django.utils.testing import GraphQLTestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import AppUser
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

    def test_upsert_creates_booking(self):
        response = self.query(
            '''
            mutation {
              upsertBookings(bookings: [{
                id: "client-1"
                reference: "EW-2026-999"
                destinationId: "dest-1"
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
            ''',
            headers=_auth_header(self.user),
        )
        self.assertResponseNoErrors(response)
        self.assertTrue(Booking.objects.filter(reference='EW-2026-999', user=self.user).exists())

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
