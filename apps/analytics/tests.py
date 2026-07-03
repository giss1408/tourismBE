import json
from graphene_django.utils.testing import GraphQLTestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import AppUser
from .models import AnalyticsEvent


def _auth_header(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'AUTHORIZATION': f'Bearer {token}'}


class TrackEventTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(
            email='tracker@example.com',
            password='pass1234!',
        )

    def test_track_event_unauthenticated_is_accepted(self):
        """Analytics tracking is allowed without auth (anonymous users)."""
        response = self.query(
            '''
            mutation {
              trackAnalyticsEvent(input: {
                name: "destination_opened"
                properties: "{\\"destination_id\\": \\"d1\\"}"
                timestamp: "2026-07-03T12:00:00Z"
              }) { ok }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        self.assertTrue(AnalyticsEvent.objects.filter(name='destination_opened').exists())

    def test_track_event_authenticated_associates_user(self):
        response = self.query(
            '''
            mutation {
              trackAnalyticsEvent(input: {
                name: "booking_confirmed"
                properties: "{\\"booking_id\\": \\"b1\\"}"
              }) { ok }
            }
            ''',
            headers=_auth_header(self.user),
        )
        self.assertResponseNoErrors(response)
        event = AnalyticsEvent.objects.get(name='booking_confirmed')
        self.assertEqual(event.user, self.user)

    def test_set_user_properties_requires_auth(self):
        response = self.query(
            '''
            mutation {
              setAnalyticsUserProperties(properties: "{\\"locale\\": \\"en\\"}") { ok }
            }
            '''
        )
        content = json.loads(response.content)
        self.assertIn('errors', content)

    def test_set_user_properties_authenticated(self):
        response = self.query(
            '''
            mutation {
              setAnalyticsUserProperties(properties: "{\\"locale\\": \\"en\\", \\"platform\\": \\"android\\"}") { ok }
            }
            ''',
            headers=_auth_header(self.user),
        )
        self.assertResponseNoErrors(response)
        from .models import UserProperties
        props = UserProperties.objects.get(user=self.user)
        self.assertEqual(props.properties.get('locale'), 'en')
