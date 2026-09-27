import io
import json
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from graphene_django.utils.testing import GraphQLTestCase
from PIL import Image
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AppUser

from .models import Destination, Media, Tour

MEDIA_DIR = tempfile.mkdtemp()


def _auth(user):
    return {'AUTHORIZATION': f'Bearer {RefreshToken.for_user(user).access_token}'}


def _photo(size=(4000, 3000)):
    """A JPEG with EXIF data, like a phone photo."""
    buffer = io.BytesIO()
    image = Image.new('RGB', size, (0, 121, 74))
    exif = Image.Exif()
    exif[0x010F] = 'PhoneMaker'  # camera make
    image.save(buffer, 'JPEG', exif=exif)
    return SimpleUploadedFile('photo.jpg', buffer.getvalue(), content_type='image/jpeg')


@override_settings(MEDIA_ROOT=MEDIA_DIR, PUBLIC_BASE_URL='https://api.test')
class ManagerApiTest(GraphQLTestCase):
    GRAPHQL_URL = '/graphql/'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_DIR, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.manager = AppUser.objects.create_user(
            email='manager@example.com', password='x', is_staff=True)
        self.traveller = AppUser.objects.create_user(email='t@example.com', password='x')
        self.destination = Destination.objects.create(
            name='Assinie', description='Plage', location="Côte d'Ivoire",
            category='Beach', price=120)

    def _upload(self, user, **fields):
        return Client().post('/manager/media/', data=fields, **{
            'HTTP_AUTHORIZATION': _auth(user)['AUTHORIZATION']})

    def test_only_managers_can_edit(self):
        content = json.loads(self.query(
            'mutation { saveDestination(input: {name: "X"}) { id } }',
            headers=_auth(self.traveller)).content)
        self.assertIn('Manager access required', content['errors'][0]['message'])
        response = self._upload(self.traveller, file=_photo(),
                                destination_id=self.destination.pk)
        self.assertEqual(response.status_code, 403)

    def test_new_destinations_are_drafts_hidden_from_travellers(self):
        created = json.loads(self.query(
            'mutation { saveDestination(input: {name: " Man ", location: "Ouest", '
            'price: 90, activities: ["Randonnée", " "]}) { id name isPublished activities } }',
            headers=_auth(self.manager)).content)['data']['saveDestination']
        self.assertEqual(created['name'], 'Man')
        self.assertFalse(created['isPublished'])
        self.assertEqual(created['activities'], ['Randonnée'])
        public = json.loads(self.query('{ destinations { name } }').content)
        self.assertNotIn('Man', [d['name'] for d in public['data']['destinations']])
        managed = json.loads(self.query('{ managerDestinations { name } }',
                                        headers=_auth(self.manager)).content)
        self.assertIn('Man', [d['name'] for d in managed['data']['managerDestinations']])

    def test_photo_upload_is_resized_and_stripped(self):
        response = self._upload(self.manager, file=_photo(),
                                destination_id=self.destination.pk)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['url'].startswith('https://api.test/media/'))
        media = Media.objects.get()
        with Image.open(media.file.path) as stored:
            self.assertEqual(max(stored.size), 1920)
            self.assertEqual(len(stored.getexif()), 0)
        data = json.loads(self.query(
            '{ destinations { images } }').content)['data']['destinations'][0]
        self.assertEqual(data['images'], [response.json()['url']])

    def test_unsupported_files_are_rejected(self):
        response = self._upload(self.manager, destination_id=self.destination.pk,
                                file=SimpleUploadedFile('notes.pdf', b'%PDF', 'application/pdf'))
        self.assertEqual(response.status_code, 400)

    def test_reorder_sets_the_cover_and_delete_removes_the_file(self):
        first = self._upload(self.manager, file=_photo((800, 600)),
                             destination_id=self.destination.pk).json()
        second = self._upload(self.manager, file=_photo((600, 800)),
                              destination_id=self.destination.pk).json()
        self.query('mutation($ids: [ID]!) { reorderMedia(ids: $ids) { ok } }',
                   variables={'ids': [second['id'], first['id']]},
                   headers=_auth(self.manager))
        images = json.loads(self.query('{ destinations { images } }').content)[
            'data']['destinations'][0]['images']
        self.assertEqual(images, [second['url'], first['url']])
        path = Media.objects.get(pk=second['id']).file.path
        self.query('mutation($id: ID!) { deleteMedia(id: $id) { ok } }',
                   variables={'id': second['id']}, headers=_auth(self.manager))
        self.assertFalse(Media.objects.filter(pk=second['id']).exists())
        import os
        self.assertFalse(os.path.exists(path))

    def test_tours_are_public_once_published(self):
        saved = json.loads(self.query(
            'mutation($d: ID!) { saveTour(input: {destinationId: $d, title: "Pirogue", '
            'durationHours: 2.5, price: 35, languages: ["fr", "de", "xx"]}) '
            '{ id isPublished languages } }',
            variables={'d': self.destination.pk}, headers=_auth(self.manager)).content)
        tour = saved['data']['saveTour']
        self.assertFalse(tour['isPublished'])
        self.assertEqual(tour['languages'], ['fr', 'de'])
        tours = lambda: json.loads(self.query('{ destinations { tours { title } } }')
                                   .content)['data']['destinations'][0]['tours']
        self.assertEqual(tours(), [])
        self.query('mutation($id: ID!) { saveTour(id: $id, input: {title: "Pirogue", '
                   'isPublished: true}) { id } }',
                   variables={'id': tour['id']}, headers=_auth(self.manager))
        self.assertEqual(tours(), [{'title': 'Pirogue'}])
        video = SimpleUploadedFile('tour.mp4', b'\x00\x00\x00\x18ftypmp42', 'video/mp4')
        response = self._upload(self.manager, file=video, tour_id=tour['id'])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['kind'], 'video')
        self.assertEqual(len(Tour.objects.get().video_urls()), 1)
