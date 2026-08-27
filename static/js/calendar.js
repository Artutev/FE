/**
 * Event Calendar Interactive Module
 * Handles event registration/unregistration through calendar popup
 */

class EventCalendar {
    constructor() {
        this.popup = document.getElementById('eventPopup');
        this.popupClose = document.querySelector('.popup-close');
        this.currentEventId = null;
        this.calendarRoot = document.getElementById('calendarRoot');
        this.calendarTitle = document.getElementById('calendarTitle');
        this.navContainer = document.querySelector('.calendar-nav');
        this.registeredEventsData = this.loadRegisteredEvents();

        this.currentMonth = this.navContainer ? parseInt(this.navContainer.dataset.month, 10) : new Date().getMonth() + 1;
        this.currentYear = this.navContainer ? parseInt(this.navContainer.dataset.year, 10) : new Date().getFullYear();

        this.init();
        this.renderCalendar();
    }

    loadRegisteredEvents() {
        const eventsData = document.getElementById('registeredEventsData');
        if (!eventsData) {
            return [];
        }

        try {
            return JSON.parse(eventsData.textContent || '[]');
        } catch (error) {
            console.error('Failed to parse registered events JSON:', error);
            return [];
        }
    }

    init() {
        // Close button
        if (this.popupClose) {
            this.popupClose.addEventListener('click', () => this.hidePopup());
        }

        // Click outside to close
        if (this.popup) {
            this.popup.addEventListener('click', (e) => {
                if (e.target === this.popup) {
                    this.hidePopup();
                }
            });
        }

        // Register button
        const registerBtn = document.getElementById('registerBtn');
        if (registerBtn) {
            registerBtn.addEventListener('click', () => this.registerEvent());
        }

        // Unregister button
        const unregisterBtn = document.getElementById('unregisterBtn');
        if (unregisterBtn) {
            unregisterBtn.addEventListener('click', () => this.unregisterEvent());
        }

        // Keyboard escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hidePopup();
            }
        });

        // Calendar navigation buttons
        const prevBtn = document.querySelector('.prev-month');
        const nextBtn = document.querySelector('.next-month');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.navigateMonth(-1));
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.navigateMonth(1));
        }
    }

    showPopup(eventId, eventName, eventDate, eventTime, eventLocation, isRegistered) {
        this.currentEventId = eventId;
        document.getElementById('popupEventName').textContent = eventName;
        document.getElementById('popupEventDate').textContent = eventDate;
        document.getElementById('popupEventTime').textContent = eventTime;
        document.getElementById('popupEventLocation').textContent = eventLocation;

        const registerBtn = document.getElementById('registerBtn');
        const unregisterBtn = document.getElementById('unregisterBtn');
        const detailBtn = document.getElementById('detailBtn');

        if (isRegistered) {
            if (registerBtn) registerBtn.style.display = 'none';
            if (unregisterBtn) unregisterBtn.style.display = 'block';
        } else {
            if (registerBtn) registerBtn.style.display = 'block';
            if (unregisterBtn) unregisterBtn.style.display = 'none';
        }

        if (detailBtn) {
            detailBtn.href = `/Events/${eventId}/`;
        }

        if (this.popup) {
            this.popup.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    hidePopup() {
        if (this.popup) {
            this.popup.classList.remove('active');
        }
        document.body.style.overflow = 'auto';
        this.currentEventId = null;
    }

    registerEvent() {
        if (!this.currentEventId) return;
        window.location.href = `/Events/${this.currentEventId}/register/`;
    }

    unregisterEvent() {
        if (!this.currentEventId) return;

        if (!confirm('Вы уверены, что хотите отменить регистрацию?')) {
            return;
        }

        window.location.href = `/Events/${this.currentEventId}/unregister/`;
    }

    navigateMonth(offset) {
        this.currentMonth += offset;

        if (this.currentMonth > 12) {
            this.currentMonth = 1;
            this.currentYear += 1;
        } else if (this.currentMonth < 1) {
            this.currentMonth = 12;
            this.currentYear -= 1;
        }

        this.updateNavData();
        this.updateUrl();
        this.renderCalendar();
    }

    updateNavData() {
        if (!this.navContainer) return;
        this.navContainer.dataset.month = this.currentMonth;
        this.navContainer.dataset.year = this.currentYear;
    }

    updateUrl() {
        const newUrl = `${window.location.pathname}?month=${this.currentMonth}&year=${this.currentYear}`;
        window.history.replaceState({}, '', newUrl);
    }

    renderCalendar() {
        if (!this.calendarRoot) return;

        const title = this.calendarTitle;
        if (title) {
            title.textContent = `${this.getMonthName(this.currentMonth)} ${this.currentYear}`;
        }

        const weeks = this.buildMonthCalendar(this.currentYear, this.currentMonth);
        const eventsByDay = this.groupEventsByDay(this.currentYear, this.currentMonth);

        const table = document.createElement('table');
        table.className = 'event-calendar';

        const thead = document.createElement('thead');
        thead.innerHTML = '<tr><th>Пн</th><th>Вт</th><th>Ср</th><th>Чт</th><th>Пт</th><th>Сб</th><th>Вс</th></tr>';
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        weeks.forEach(week => {
            const row = document.createElement('tr');
            week.forEach(day => {
                const cell = document.createElement('td');
                if (day === 0) {
                    cell.classList.add('empty');
                } else {
                    cell.innerHTML = `<span class="day-number">${day}</span>`;
                    const dayEvents = eventsByDay[day] || [];
                    if (dayEvents.length > 0) {
                        const eventsWrapper = document.createElement('div');
                        eventsWrapper.className = 'day-events';
                        dayEvents.forEach(event => {
                            const link = document.createElement('a');
                            link.href = '#';
                            link.className = 'event-link';
                            link.textContent = event.name;
                            link.dataset.eventId = event.id;
                            link.dataset.eventName = event.name;
                            link.dataset.eventDate = event.dateLabel;
                            link.dataset.eventTime = event.time;
                            link.dataset.eventLocation = event.location;
                            link.dataset.registered = event.registered ? 'true' : 'false';
                            link.addEventListener('click', (e) => {
                                e.preventDefault();
                                this.showPopup(
                                    event.id,
                                    event.name,
                                    event.dateLabel,
                                    event.time,
                                    event.location,
                                    event.registered
                                );
                            });
                            eventsWrapper.appendChild(link);
                        });
                        cell.appendChild(eventsWrapper);
                    }
                }
                row.appendChild(cell);
            });
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        this.calendarRoot.innerHTML = '';
        this.calendarRoot.appendChild(table);
    }

    groupEventsByDay(year, month) {
        const grouped = {};
        this.registeredEventsData.forEach(event => {
            const eventDate = new Date(event.date);
            const eventYear = eventDate.getFullYear();
            const eventMonth = eventDate.getMonth() + 1;
            const eventDay = eventDate.getDate();

            if (eventYear === year && eventMonth === month) {
                const formattedDate = eventDate.toLocaleDateString('ru-RU', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                });

                const eventData = {
                    id: event.id,
                    name: event.name,
                    dateLabel: formattedDate,
                    time: event.time || '',
                    location: event.location || '',
                    registered: event.registered
                };

                if (!grouped[eventDay]) {
                    grouped[eventDay] = [];
                }
                grouped[eventDay].push(eventData);
            }
        });
        return grouped;
    }

    buildMonthCalendar(year, month) {
        const firstDay = new Date(year, month - 1, 1).getDay();
        const daysInMonth = new Date(year, month, 0).getDate();

        const firstMondayOffset = (firstDay + 6) % 7;
        const weeks = [];
        let week = Array(firstMondayOffset).fill(0);

        for (let day = 1; day <= daysInMonth; day += 1) {
            week.push(day);
            if (week.length === 7) {
                weeks.push(week);
                week = [];
            }
        }

        if (week.length > 0) {
            while (week.length < 7) {
                week.push(0);
            }
            weeks.push(week);
        }

        return weeks;
    }

    getMonthName(month) {
        const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
        return monthNames[month - 1] || '';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new EventCalendar();
});
