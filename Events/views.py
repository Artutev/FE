from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
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
    events = Event.objects.all().order_by('date', 'time')  # сортировка по дате и времени
    context = {'events': events}
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