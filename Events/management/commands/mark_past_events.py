from django.core.management.base import BaseCommand
from django.utils import timezone

from Events.models import Event


class Command(BaseCommand):
    help = 'Пометить прошедшие мероприятия (is_past=True) по дате события.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        qs = Event.objects.filter(is_past=False).exclude(date__isnull=True)
        count = 0
        for ev in qs:
            if ev.date < today:
                ev.is_past = True
                ev.save(update_fields=['is_past'])
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Marked {count} events as past.'))