from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from Events.models import Event
from Events.forms import EventForm

def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.creator = request.user
            event.save()
            return redirect('Events:event_list')
    else:
        form = EventForm()
    context = {'form': form}

    return render(request, 'Events/event.html', context)

def event_list(request):
    events = Event.objects.all().order_by('date', 'time')
    
    # Фильтр по типу события
    event_type = request.GET.get('type', '')
    if event_type and event_type != 'all':
        events = events.filter(event_type=event_type)
    
    # Поиск мероприятий (исправлено для работы с Cyrillic символами)
    search_query = request.GET.get('search', '')
    if search_query:
        search_lower = search_query.lower()
        events = [
            event for event in events
            if (search_lower in event.name.lower() or
                search_lower in event.description.lower() or
                search_lower in event.location.lower())
        ]
    
    context = {
        'events': events,
        'search_query': search_query,
        'event_type': event_type,
        'event_types': Event.event_types
    }
    return render(request, 'Events/eventList.html', context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    context = {'event': event}
    return render(request, 'Events/eventDetail.html', context)

@login_required(login_url='Users:login')
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('Users:profile')
    else:
        form = EventForm(instance=event)

    return render(request, 'Events/eventEdit.html', {'form': form, 'event': event})


@login_required(login_url='Users:login')
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)

    if request.method == 'POST':
        event.delete()
        return redirect('Users:profile')
    context = {'event': event}

    return render(request, 'Events/eventDeleteConfirm.html', context)