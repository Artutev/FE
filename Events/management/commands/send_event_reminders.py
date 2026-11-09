from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from Events.models import Event
from Events.notifications import send_reminders


class Command(BaseCommand):
    help = 'Отправить напоминания участникам мероприятий, которые пройдут завтра. Запускать по cron раз в день.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Только показать, кому ушли бы напоминания.')

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)
        events = list(Event.objects.filter(date=tomorrow, reminder_sent=False))
        if options['dry_run']:
            for event in events:
                count = event.registrations.filter(user__email_notifications=True, user__is_active=True).count()
                self.stdout.write(f'{event.id} {event.name}: {count} recipient(s)')
            return
        sent_events, sent_messages = send_reminders(events)
        self.stdout.write(self.style.SUCCESS(f'Reminders: {sent_events} event(s), {sent_messages} email(s).'))
