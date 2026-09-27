import json
from django.test import TestCase
from graphene_django.utils.testing import GraphQLTestCase
from apps.accounts.models import AppUser


class SignUpMutationTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def test_sign_up_creates_user_and_returns_token(self):
        response = self.query(
            '''
            mutation {
              signUp(
                email: "new@example.com"
                password: "Str0ng!Pass"
                displayName: "New User"
              ) {
                uid
                email
                displayName
                accessToken
              }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['signUp']
        self.assertEqual(data['email'], 'new@example.com')
        self.assertIsNotNone(data['accessToken'])
        self.assertTrue(AppUser.objects.filter(email='new@example.com').exists())

    def test_sign_up_duplicate_email_raises_error(self):
        AppUser.objects.create_user(email='dup@example.com', password='pass123')
        response = self.query(
            '''
            mutation {
              signUp(
                email: "dup@example.com"
                password: "Str0ng!Pass"
                displayName: "Dup"
              ) { uid }
            }
            '''
        )
        content = json.loads(response.content)
        self.assertIn('errors', content)


class SignInMutationTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        self.user = AppUser.objects.create_user(
            email='user@example.com',
            password='pass1234!',
            display_name='Tester',
        )

    def test_sign_in_returns_token(self):
        response = self.query(
            '''
            mutation {
              signIn(email: "user@example.com", password: "pass1234!") {
                uid
                email
                accessToken
              }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['signIn']
        self.assertEqual(data['email'], 'user@example.com')
        self.assertIsNotNone(data['accessToken'])

    def test_sign_in_bad_password_raises_error(self):
        response = self.query(
            '''
            mutation {
              signIn(email: "user@example.com", password: "wrong") {
                uid
              }
            }
            '''
        )
        content = json.loads(response.content)
        self.assertIn('errors', content)

    def test_me_query_requires_auth(self):
        response = self.query('{ me { email } }')
        content = json.loads(response.content)
        self.assertIn('errors', content)


class AuthSecurityTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = AppUser.objects.create_user(
            email='secure@example.com', password='pass1234!')

    def _sign_in(self, password):
        return json.loads(self.query(
            'mutation($p: String!) { signIn(email: "secure@example.com", '
            'password: $p) { accessToken refreshToken } }',
            variables={'p': password}).content)

    def test_sign_in_is_locked_after_repeated_failures(self):
        for _ in range(5):
            self.assertEqual(self._sign_in('wrong')['errors'][0]['message'],
                             'Invalid credentials.')
        locked = self._sign_in('pass1234!')
        self.assertIn('Too many attempts', locked['errors'][0]['message'])

    def test_refresh_rotates_and_revokes_the_old_token(self):
        refresh = self._sign_in('pass1234!')['data']['signIn']['refreshToken']
        query = ('mutation($t: String!) { refreshSession(refreshToken: $t) '
                 '{ accessToken refreshToken } }')
        first = json.loads(self.query(query, variables={'t': refresh}).content)
        self.assertIsNotNone(first['data']['refreshSession']['accessToken'])
        replay = json.loads(self.query(query, variables={'t': refresh}).content)
        self.assertIn('errors', replay)

    def test_sign_out_revokes_the_refresh_token(self):
        refresh = self._sign_in('pass1234!')['data']['signIn']['refreshToken']
        self.query('mutation($t: String) { signOut(refreshToken: $t) { ok } }',
                   variables={'t': refresh})
        replay = json.loads(self.query(
            'mutation($t: String!) { refreshSession(refreshToken: $t) { accessToken } }',
            variables={'t': refresh}).content)
        self.assertIn('errors', replay)

    def test_session_cookie_is_not_trusted(self):
        admin = AppUser.objects.create_superuser(
            email='admin@example.com', password='pass1234!')
        self.client.force_login(admin)
        content = json.loads(self.query('{ me { email } }').content)
        self.assertIn('errors', content)

    def test_variable_values_are_never_logged(self):
        with self.assertLogs('tourism.graphql', level='DEBUG') as logs:
            self.query(
                'mutation($e: String!, $p: String!) { signIn(email: $e, '
                'password: $p) { uid } }',
                variables={'e': 'secure@example.com', 'p': 'S3cret-value!'})
        output = '\n'.join(logs.output)
        self.assertIn("['e', 'p']", output)
        self.assertNotIn('S3cret-value!', output)
        self.assertNotIn('secure@example.com', output)


class SocialSignInTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'
    MUTATION = ('mutation($t: String) { socialSignIn(idToken: $t, uid: "fake-uid", '
                'email: "victim@example.com", provider: "google") { email } }')

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        AppUser.objects.create_user(email='victim@example.com', password='pass1234!')

    def test_production_requires_verified_token(self):
        from unittest import mock
        from django.test import override_settings
        from apps.accounts.security import FirebaseTokenError
        with override_settings(FIREBASE_PROJECT_ID='proj'):
            missing = json.loads(self.query(self.MUTATION).content)
            self.assertIn('errors', missing)
            with mock.patch('apps.accounts.schema.verify_firebase_id_token',
                            side_effect=FirebaseTokenError('Invalid social sign-in token.')):
                forged = json.loads(self.query(
                    self.MUTATION, variables={'t': 'forged'}).content)
            self.assertIn('errors', forged)

    def test_claims_come_from_the_verified_token(self):
        from unittest import mock
        from django.test import override_settings
        claims = {'sub': 'real-uid', 'email': 'new@example.com', 'email_verified': True}
        with override_settings(FIREBASE_PROJECT_ID='proj'), \
                mock.patch('apps.accounts.schema.verify_firebase_id_token',
                           return_value=claims):
            content = json.loads(self.query(
                self.MUTATION, variables={'t': 'token'}).content)
        self.assertEqual(content['data']['socialSignIn']['email'], 'new@example.com')
        self.assertTrue(AppUser.objects.filter(firebase_uid='real-uid').exists())

    def test_unverified_email_cannot_take_over_an_account(self):
        from unittest import mock
        from django.test import override_settings
        claims = {'sub': 'other', 'email': 'victim@example.com', 'email_verified': False}
        with override_settings(FIREBASE_PROJECT_ID='proj'), \
                mock.patch('apps.accounts.schema.verify_firebase_id_token',
                           return_value=claims):
            content = json.loads(self.query(
                self.MUTATION, variables={'t': 'token'}).content)
        self.assertIn('errors', content)

    def test_production_without_firebase_refuses(self):
        from django.test import override_settings
        with override_settings(FIREBASE_PROJECT_ID='', DEBUG=False):
            content = json.loads(self.query(self.MUTATION).content)
        self.assertIn('errors', content)


class ProfileMutationsTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.user = AppUser.objects.create_user(email='p@example.com', password='Old-pass-123!')
        token = RefreshToken.for_user(self.user).access_token
        self.headers = {'AUTHORIZATION': f'Bearer {token}'}

    def test_update_display_name(self):
        content = json.loads(self.query(
            'mutation { updateProfile(displayName: " Amara ") { displayName } }',
            headers=self.headers).content)
        self.assertEqual(content['data']['updateProfile']['displayName'], 'Amara')

    def test_change_password_checks_the_current_one(self):
        wrong = json.loads(self.query(
            'mutation { changePassword(currentPassword: "nope", newPassword: "New-pass-456!") { ok } }',
            headers=self.headers).content)
        self.assertIn('errors', wrong)
        self.query(
            'mutation { changePassword(currentPassword: "Old-pass-123!", newPassword: "New-pass-456!") { ok } }',
            headers=self.headers)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('New-pass-456!'))
