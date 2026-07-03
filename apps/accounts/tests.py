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
