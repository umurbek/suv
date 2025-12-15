from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
import csv
import time
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
except Exception:
    Nominatim = None

try:
    import googlemaps
    from googlemaps.exceptions import ApiError as GoogleApiError
except Exception:
    googlemaps = None
    GoogleApiError = None

    def add_arguments(self, parser):
        parser.add_argument('--csv-path', dest='csv_path', help='Path to CSV file', default=None)
        parser.add_argument('--limit', dest='limit', type=int, help='Limit number of rows to process', default=0)
        parser.add_argument('--delay', dest='delay', type=float, help='Delay seconds between requests (Nominatim rate-limit)', default=1.0)
        parser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Do not save updates, only print')
        parser.add_argument('--force', dest='force', action='store_true', help='Overwrite existing coordinates')
        parser.add_argument('--google-key', dest='google_key', help='Google Geocoding API key (optional). If provided, Google will be used.')

    def handle(self, *args, **options):
        if Nominatim is None:
            raise CommandError('geopy is not installed. Please install with: pip install geopy')

        csv_path = options.get('csv_path') or os.path.join(getattr(settings, 'BASE_DIR', '.'), 'Volidam.csv')
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')

        limit = int(options.get('limit') or 0)
        delay = float(options.get('delay') or 1.0)
        dry_run = bool(options.get('dry_run'))
        force = bool(options.get('force'))

        # Choose provider: Google if key provided and googlemaps installed, otherwise Nominatim
        google_key = options.get('google_key')
        # allow reading from environment or Django settings if not passed
        if not google_key:
            google_key = getattr(settings, 'GOOGLE_API_KEY', None) or os.environ.get('GOOGLE_API_KEY')

        use_google = bool(google_key and googlemaps is not None)
        if use_google:
            self.stdout.write(self.style.NOTICE('Using Google Geocoding API'))
            gmaps = googlemaps.Client(key=google_key)
        else:
            if Nominatim is None:
                raise CommandError('geopy is not installed. Please install with: pip install geopy')
            geolocator = Nominatim(user_agent='crm_geocoder_2025')

        self.stdout.write(self.style.NOTICE(f'Geocoding CSV: {csv_path} (limit={limit or "all"}, delay={delay}s)'))

        processed = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for idx, row in enumerate(reader):
                if limit and processed >= limit:
                    break
                # Expecting: name, bottle, location, phone
                name = (row[0] if len(row) > 0 else '') or ''
                location_text = (row[2] if len(row) > 2 else '') or ''
                phone = (row[3] if len(row) > 3 else '') or ''

                if not name or not location_text:
                    self.stdout.write(self.style.WARNING(f'Skipping row {idx+1}: missing name or location'))
                    continue

                try:
                    # Try geocoding; use Google if configured otherwise Nominatim
                    geocode_result = None
                    lat = None
                    lon = None
                    if use_google:
                        try:
                            res = gmaps.geocode(location_text)
                            if res and len(res) > 0:
                                loc = res[0]['geometry']['location']
                                lat = float(loc.get('lat'))
                                lon = float(loc.get('lng'))
                            else:
                                self.stdout.write(self.style.WARNING(f'No geocode for "{name}" -> "{location_text}" (Google)'))
                                processed += 1
                                time.sleep(delay)
                                continue
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'Google geocode error for "{location_text}": {e}'))
                            processed += 1
                            time.sleep(delay)
                            continue
                    else:
                        # Nominatim with retry
                        attempts = 0
                        while attempts < 3:
                            try:
                                geocode_result = geolocator.geocode(location_text, timeout=10)
                                break
                            except GeocoderTimedOut:
                                attempts += 1
                                time.sleep(1)
                            except GeocoderServiceError as e:
                                self.stdout.write(self.style.ERROR(f'Geocoder service error: {e}'))
                                break

                        if not geocode_result:
                            self.stdout.write(self.style.WARNING(f'No geocode for "{name}" -> "{location_text}"'))
                            processed += 1
                            time.sleep(delay)
                            continue

                        lat = geocode_result.latitude
                        lon = geocode_result.longitude

                    self.stdout.write(self.style.SUCCESS(f'Row {idx+1}: {name} -> {lat:.6f},{lon:.6f}'))

                    # Find clients with matching region name
                    region_objs = Region.objects.filter(name__iexact=name)
                    if not region_objs.exists():
                        # try partial match
                        region_objs = Region.objects.filter(name__icontains=name)

                    if not region_objs.exists():
                        self.stdout.write(self.style.WARNING(f'No Region found for "{name}". Skipping client updates.'))
                    else:
                        for region in region_objs:
                            clients = Client.objects.filter(region=region)
                            if not clients.exists():
                                self.stdout.write(self.style.WARNING(f'No Clients found for Region "{region.name}"'))
                                continue
                            for c in clients:
                                cur_lat = getattr(c, 'location_lat', 0) or 0
                                cur_lon = getattr(c, 'location_lon', 0) or 0
                                if (cur_lat == 0 and cur_lon == 0) or force:
                                    self.stdout.write(f'  -> Updating Client {c.id} ({c.full_name})')
                                    if not dry_run:
                                        c.location_lat = lat
                                        c.location_lon = lon
                                        c.save()
                                else:
                                    self.stdout.write(f'  -> Skipping Client {c.id} ({c.full_name}) (coords exist)')

                    processed += 1
                    time.sleep(delay)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing row {idx+1}: {e}'))
                    processed += 1
                    time.sleep(delay)

        self.stdout.write(self.style.NOTICE(f'Finished. Processed {processed} rows.'))
