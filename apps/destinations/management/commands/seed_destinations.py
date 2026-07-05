from django.core.management.base import BaseCommand
from apps.destinations.models import Destination

SEED_DESTINATIONS = [
    # ── Sample destinations (match Flutter _sampleDestinations) ─────────────
    {
        'id': 1,
        'name': 'Santorini Cliffs',
        'location': 'Santorini, Greece',
        'description': 'Whitewashed houses, blue domes and stunning sunsets over the caldera.',
        'rating': 4.8,
        'price': 249.0,
        'category': 'Beach',
        'images': [
            'https://picsum.photos/id/1018/800/600',
            'https://picsum.photos/id/1015/800/600',
        ],
        'activities': ['Sightseeing', 'Sunset Viewing', 'Photography'],
        'is_featured': True,
        'available_spots': 30,
        'discount': 0.0,
        'latitude': 36.3932,
        'longitude': 25.4615,
    },
    {
        'id': 2,
        'name': 'Machu Picchu',
        'location': 'Cusco Region, Peru',
        'description': 'Ancient Incan citadel set high in the Andes Mountains, a bucket-list trek.',
        'rating': 4.9,
        'price': 399.0,
        'category': 'Historical',
        'images': [
            'https://picsum.photos/id/1025/800/600',
            'https://picsum.photos/id/1024/800/600',
        ],
        'activities': ['Hiking', 'Guided Tours', 'Photography'],
        'is_featured': True,
        'available_spots': 20,
        'discount': 0.1,
        'latitude': -13.1631,
        'longitude': -72.545,
    },
    {
        'id': 3,
        'name': 'Bali Rice Terraces',
        'location': 'Ubud, Indonesia',
        'description': 'Lush green terraces, local culture, yoga retreats and hidden waterfalls.',
        'rating': 4.6,
        'price': 129.0,
        'category': 'Adventure',
        'images': [
            'https://picsum.photos/id/1036/800/600',
            'https://picsum.photos/id/1035/800/600',
        ],
        'activities': ['Trekking', 'Cultural Tours', 'Yoga Retreats'],
        'is_featured': False,
        'available_spots': 50,
        'discount': 0.0,
        'latitude': -8.5069,
        'longitude': 115.2625,
    },
    {
        'id': 4,
        'name': 'Kyoto Temples',
        'location': 'Kyoto, Japan',
        'description': 'Historic temples, traditional tea houses and serene bamboo groves.',
        'rating': 4.7,
        'price': 179.0,
        'category': 'Historical',
        'images': [
            'https://picsum.photos/id/1043/800/600',
            'https://picsum.photos/id/1041/800/600',
        ],
        'activities': ['Temple Visits', 'Tea Ceremonies', 'Walking Tours'],
        'is_featured': False,
        'available_spots': 40,
        'discount': 0.05,
        'latitude': 35.0116,
        'longitude': 135.7681,
    },
    {
        'id': 5,
        'name': 'Swiss Alps Retreat',
        'location': 'Zermatt, Switzerland',
        'description': 'Ski slopes, alpine villages and breathtaking Matterhorn views.',
        'rating': 4.9,
        'price': 499.0,
        'category': 'Mountain',
        'images': [
            'https://picsum.photos/id/1056/800/600',
            'https://picsum.photos/id/1054/800/600',
        ],
        'activities': ['Skiing', 'Hiking', 'Cable Car Rides'],
        'is_featured': True,
        'available_spots': 15,
        'discount': 0.0,
        'latitude': 46.0207,
        'longitude': 7.7491,
    },
    {
        'id': 6,
        'name': 'New York City',
        'location': 'New York, USA',
        'description': 'Iconic skyline, museums, Broadway shows and vibrant neighborhoods.',
        'rating': 4.5,
        'price': 199.0,
        'category': 'City',
        'images': [
            'https://picsum.photos/id/1069/800/600',
            'https://picsum.photos/id/1070/800/600',
        ],
        'activities': ['City Tours', 'Museums', 'Food Tours'],
        'is_featured': False,
        'available_spots': 100,
        'discount': 0.15,
        'latitude': 40.7128,
        'longitude': -74.006,
    },
    {
        'id': 7,
        'name': 'Table Mountain',
        'location': 'Cape Town, South Africa',
        'description': 'Flat-topped mountain with cable car access and panoramic city views.',
        'rating': 4.7,
        'price': 149.0,
        'category': 'Adventure',
        'images': [
            'https://picsum.photos/id/1080/800/600',
            'https://picsum.photos/id/1082/800/600',
        ],
        'activities': ['Cable Car', 'Hiking', 'Panoramic Viewing'],
        'is_featured': True,
        'available_spots': 60,
        'discount': 0.0,
        'latitude': -33.9628,
        'longitude': 18.4098,
    },
    # ── Fallback destinations (match Flutter _fallbackDestinations) ──────────
    {
        'id': 8,
        'name': 'Bali Paradise',
        'location': 'Bali, Indonesia',
        'description': 'Beautiful tropical island with stunning beaches and rich culture.',
        'rating': 4.8,
        'price': 299.99,
        'category': 'Beach',
        'images': ['https://picsum.photos/400/300?random=1'],
        'activities': ['Beach', 'Surfing', 'Temples'],
        'is_featured': True,
        'available_spots': 50,
        'discount': 0.0,
        'latitude': -8.4095,
        'longitude': 115.1889,
    },
    {
        'id': 9,
        'name': 'Tokyo Adventure',
        'location': 'Tokyo, Japan',
        'description': 'Experience the perfect blend of tradition and modernity.',
        'rating': 4.7,
        'price': 599.99,
        'category': 'City',
        'images': ['https://picsum.photos/400/300?random=2'],
        'activities': ['City Tour', 'Shopping', 'Temples'],
        'is_featured': True,
        'available_spots': 40,
        'discount': 0.1,
        'latitude': 35.6762,
        'longitude': 139.6503,
    },
    {
        'id': 10,
        'name': 'Swiss Alps',
        'location': 'Interlaken, Switzerland',
        'description': 'Breathtaking mountain views and outdoor activities.',
        'rating': 4.9,
        'price': 799.99,
        'category': 'Mountain',
        'images': ['https://picsum.photos/400/300?random=3'],
        'activities': ['Hiking', 'Skiing', 'Sightseeing'],
        'is_featured': False,
        'available_spots': 25,
        'discount': 0.0,
        'latitude': 46.6863,
        'longitude': 7.8632,
    },
    # ── Extra destinations for richer testing ────────────────────────────────
    {
        'id': 11,
        'name': 'Amalfi Coast',
        'location': 'Salerno, Italy',
        'description': 'Dramatic cliffs, colourful fishing villages and azure waters.',
        'rating': 4.8,
        'price': 329.0,
        'category': 'Beach',
        'images': ['https://picsum.photos/id/1011/800/600'],
        'activities': ['Boat Tours', 'Hiking', 'Food Tasting'],
        'is_featured': True,
        'available_spots': 35,
        'discount': 0.1,
        'latitude': 40.6333,
        'longitude': 14.6029,
    },
    {
        'id': 12,
        'name': 'Sahara Desert',
        'location': 'Merzouga, Morocco',
        'description': 'Golden dunes, camel rides and stargazing under boundless skies.',
        'rating': 4.6,
        'price': 219.0,
        'category': 'Adventure',
        'images': ['https://picsum.photos/id/1003/800/600'],
        'activities': ['Camel Trekking', 'Camping', 'Stargazing'],
        'is_featured': False,
        'available_spots': 20,
        'discount': 0.0,
        'latitude': 31.0998,
        'longitude': -4.0133,
    },
    {
        'id': 13,
        'name': 'Northern Lights Iceland',
        'location': 'Reykjavik, Iceland',
        'description': 'Chase the aurora borealis across volcanic landscapes and geysers.',
        'rating': 4.9,
        'price': 549.0,
        'category': 'Adventure',
        'images': ['https://picsum.photos/id/1002/800/600'],
        'activities': ['Aurora Watching', 'Hot Springs', 'Whale Watching'],
        'is_featured': True,
        'available_spots': 18,
        'discount': 0.05,
        'latitude': 64.1355,
        'longitude': -21.8954,
    },
    {
        'id': 14,
        'name': 'Angkor Wat',
        'location': 'Siem Reap, Cambodia',
        'description': 'The world\'s largest religious monument surrounded by jungle.',
        'rating': 4.8,
        'price': 189.0,
        'category': 'Historical',
        'images': ['https://picsum.photos/id/1074/800/600'],
        'activities': ['Temple Tours', 'Sunrise Viewing', 'Cycling'],
        'is_featured': False,
        'available_spots': 45,
        'discount': 0.0,
        'latitude': 13.4125,
        'longitude': 103.8670,
    },
]


class Command(BaseCommand):
    help = 'Seed the database with mock destinations matching the tourismApp sample data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing destinations before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count, _ = Destination.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing destination(s).'))

        created = 0
        updated = 0

        for data in SEED_DESTINATIONS:
            obj, is_new = Destination.objects.update_or_create(
                pk=data['id'],
                defaults={k: v for k, v in data.items() if k != 'id'},
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded destinations: {created} created, {updated} updated.'
            )
        )
