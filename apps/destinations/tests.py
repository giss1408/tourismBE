import json
from graphene_django.utils.testing import GraphQLTestCase
from .models import Destination


class DestinationQueryTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    def setUp(self):
        Destination.objects.create(
            name='Paris',
            description='City of lights',
            location='France',
            rating=4.8,
            price=250.0,
            images=['https://example.com/paris.jpg'],
            activities=['Walk', 'Tour'],
            is_featured=True,
            category='City',
        )
        Destination.objects.create(
            name='Bali',
            description='Island paradise',
            location='Indonesia',
            rating=4.9,
            price=180.0,
            images=['https://example.com/bali.jpg'],
            activities=['Surf', 'Yoga'],
            is_featured=False,
            category='Beach',
        )

    def test_fetch_all_destinations(self):
        response = self.query(
            '''
            {
              destinations {
                id
                name
                location
                category
              }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['destinations']
        self.assertEqual(len(data), 2)

    def test_filter_by_category(self):
        response = self.query(
            '''
            {
              destinations(category: "Beach") {
                name
                category
              }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['destinations']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Bali')

    def test_search_by_name(self):
        response = self.query(
            '''
            {
              destinations(search: "paris") {
                name
              }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['destinations']
        self.assertEqual(data[0]['name'], 'Paris')

    def test_destination_by_id(self):
        dest = Destination.objects.first()
        response = self.query(
            f'''
            {{
              destination(id: "{dest.pk}") {{
                name
              }}
            }}
            '''
        )
        self.assertResponseNoErrors(response)
        data = json.loads(response.content)['data']['destination']
        self.assertEqual(data['name'], dest.name)

    def test_destination_not_found_raises_error(self):
        response = self.query('{ destination(id: "99999") { name } }')
        content = json.loads(response.content)
        self.assertIn('errors', content)
