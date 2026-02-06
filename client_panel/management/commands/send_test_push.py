from django.core.management.base import BaseCommand
from client_panel.models import PushToken
from suv_tashish_crm.notifications import send_fcm


class Command(BaseCommand):
    help = 'Send test push to a token or all registered tokens'

    def add_arguments(self, parser):
        parser.add_argument('--token', help='Send only to this device token')
        parser.add_argument('--title', default='Test notification', help='Notification title')
        parser.add_argument('--body', default='Hello from server', help='Notification body')

    def handle(self, *args, **options):
        token = options.get('token')
        title = options.get('title')
        body = options.get('body')

        if token:
            self.stdout.write('Sending to single token...')
            result = send_fcm(token, title, body)
        else:
            tokens = list(PushToken.objects.values_list('token', flat=True))
            if not tokens:
                self.stdout.write('No tokens registered')
                return
            self.stdout.write(f'Sending to {len(tokens)} tokens...')
            result = send_fcm(tokens, title, body)

        self.stdout.write(str(result))
