document.addEventListener('DOMContentLoaded', () => {
    const dateInputs = document.querySelectorAll('.date-picker-input');
    const timeInputs = document.querySelectorAll('.time-picker-input');

    function createPopup() {
        const popup = document.createElement('div');
        popup.className = 'picker-popup hidden';
        popup.innerHTML = `
            <div class="picker-header">
                <button type="button" class="picker-prev">‹</button>
                <div class="picker-title-group">
                    <div class="picker-title"></div>
                    <div class="picker-year-control">
                        <button type="button" class="picker-year-prev" aria-label="Previous year">‹</button>
                        <input class="picker-year" type="number" aria-label="Year" min="1900" max="2100">
                        <button type="button" class="picker-year-next" aria-label="Next year">›</button>
                    </div>
                </div>
                <button type="button" class="picker-next">›</button>
            </div>
            <div class="calendar-grid"></div>
            <div class="time-list"></div>
        `;
        document.body.appendChild(popup);
        return popup;
    }

    function formatDate(year, month, day) {
        const mm = String(month + 1).padStart(2, '0');
        const dd = String(day).padStart(2, '0');
        return `${year}-${mm}-${dd}`;
    }

    function updateDateInput(input, year, month, day) {
        input.value = formatDate(year, month, day);
    }

    function closePopup(popup) {
        popup.classList.add('hidden');
    }

    function openPopup(popup, input) {
        popup.classList.remove('hidden');
        const rect = input.getBoundingClientRect();
        popup.style.top = `${rect.bottom + window.scrollY + 10}px`;
        popup.style.left = `${rect.left + window.scrollX}px`;
        popup.style.minWidth = `${rect.width}px`;
    }

    function buildCalendar(popup, input, year, month) {
        const title = popup.querySelector('.picker-title');
        const grid = popup.querySelector('.calendar-grid');
        const prevBtn = popup.querySelector('.picker-prev');
        const nextBtn = popup.querySelector('.picker-next');
        const yearSelect = popup.querySelector('.picker-year');
        const yearPrevBtn = popup.querySelector('.picker-year-prev');
        const yearNextBtn = popup.querySelector('.picker-year-next');

        title.textContent = new Date(year, month, 1).toLocaleDateString(undefined, {
            month: 'long'
        });
        yearSelect.value = year;
        yearSelect.style.display = 'block';
        yearSelect.onchange = () => {
            const selectedYear = Math.min(2100, Math.max(1900, Number(yearSelect.value)));
            yearSelect.value = selectedYear;
            buildCalendar(popup, input, selectedYear, month);
        };
        yearPrevBtn.style.display = 'inline-flex';
        yearNextBtn.style.display = 'inline-flex';
        yearPrevBtn.onclick = () => buildCalendar(popup, input, Math.max(1900, year - 1), month);
        yearNextBtn.onclick = () => buildCalendar(popup, input, Math.min(2100, year + 1), month);
        grid.innerHTML = '';

        const weekdays = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
        weekdays.forEach(day => {
            const span = document.createElement('span');
            span.className = 'weekday';
            span.textContent = day;
            grid.appendChild(span);
        });

        const firstDay = new Date(year, month, 1).getDay();
        const offset = firstDay === 0 ? 6 : firstDay - 1;
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        for (let i = 0; i < offset; i += 1) {
            const empty = document.createElement('button');
            empty.className = 'empty';
            empty.disabled = true;
            empty.textContent = '';
            grid.appendChild(empty);
        }

        for (let day = 1; day <= daysInMonth; day += 1) {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = day;
            button.addEventListener('click', () => {
                updateDateInput(input, year, month, day);
                closePopup(popup);
            });
            grid.appendChild(button);
        }

        prevBtn.onclick = () => {
            const prevMonth = month === 0 ? 11 : month - 1;
            const prevYear = month === 0 ? year - 1 : year;
            buildCalendar(popup, input, prevYear, prevMonth);
        };

        nextBtn.onclick = () => {
            const nextMonth = month === 11 ? 0 : month + 1;
            const nextYear = month === 11 ? year + 1 : year;
            buildCalendar(popup, input, nextYear, nextMonth);
        };
    }

    function getCurrentDateParts(input) {
        if (input.value) {
            const [year, month, day] = input.value.split('-').map(Number);
            return [year, month - 1, day];
        }
        const now = new Date();
        return [now.getFullYear(), now.getMonth(), now.getDate()];
    }

    function getCurrentTimeParts(input) {
        if (input.value) {
            const [hour, minute] = input.value.split(':').map(Number);
            if (!Number.isNaN(hour) && !Number.isNaN(minute)) {
                return [hour, minute];
            }
        }
        const now = new Date();
        return [now.getHours(), now.getMinutes()];
    }

    const popups = [];

    dateInputs.forEach(input => {
        const popup = createPopup();
        popups.push(popup);

        input.addEventListener('focus', () => {
            const [year, month] = getCurrentDateParts(input);
            buildCalendar(popup, input, year, month);
            openPopup(popup, input);
        });

        input.addEventListener('click', () => {
            const [year, month] = getCurrentDateParts(input);
            buildCalendar(popup, input, year, month);
            openPopup(popup, input);
        });
    });

    function buildTimePopup(popup, input) {
        const title = popup.querySelector('.picker-title');
        const grid = popup.querySelector('.time-list');
        const prevBtn = popup.querySelector('.picker-prev');
        const nextBtn = popup.querySelector('.picker-next');
        const yearSelect = popup.querySelector('.picker-year');
        const yearPrevBtn = popup.querySelector('.picker-year-prev');
        const yearNextBtn = popup.querySelector('.picker-year-next');

        title.textContent = 'Time';
        grid.innerHTML = '';
        yearSelect.style.display = 'none';
        yearPrevBtn.style.display = 'none';
        yearNextBtn.style.display = 'none';
        prevBtn.style.visibility = 'hidden';
        nextBtn.style.visibility = 'hidden';

        const [currentHour, currentMinute] = getCurrentTimeParts(input);
        let selectedHour = currentHour;
        let selectedMinute = currentMinute;

        function createSpinner(labelText, initialValue, min, max) {
            const group = document.createElement('div');
            group.className = 'spinner-group';

            const titleEl = document.createElement('div');
            titleEl.className = 'spinner-title';
            titleEl.textContent = labelText;

            const control = document.createElement('div');
            control.className = 'spinner-control';

            const prevEl = document.createElement('button');
            prevEl.type = 'button';
            prevEl.className = 'spinner-nav';

            const valueEl = document.createElement('div');
            valueEl.className = 'spinner-current';
            valueEl.textContent = String(initialValue).padStart(2, '0');

            const nextEl = document.createElement('button');
            nextEl.type = 'button';
            nextEl.className = 'spinner-nav';

            let currentValue = initialValue;

            function updateValue(value) {
                if (value < min) value = max;
                if (value > max) value = min;
                currentValue = value;
                const prevValue = value === min ? max : value - 1;
                const nextValue = value === max ? min : value + 1;
                prevEl.textContent = String(prevValue).padStart(2, '0');
                valueEl.textContent = String(value).padStart(2, '0');
                nextEl.textContent = String(nextValue).padStart(2, '0');
            }

            prevEl.addEventListener('click', () => updateValue(currentValue - 1));
            nextEl.addEventListener('click', () => updateValue(currentValue + 1));

            control.addEventListener('wheel', (event) => {
                event.preventDefault();
                const delta = event.deltaY < 0 ? 1 : -1;
                updateValue(currentValue + delta);
            });

            control.appendChild(prevEl);
            control.appendChild(valueEl);
            control.appendChild(nextEl);
            group.appendChild(titleEl);
            group.appendChild(control);

            updateValue(initialValue);

            return {
                element: group,
                getValue: () => currentValue,
                setValue: updateValue,
            };
        }

        const hourSpinner = createSpinner('Hour', selectedHour, 0, 23);
        const minuteSpinner = createSpinner('Minute', selectedMinute, 0, 59);

        const actionRow = document.createElement('div');
        actionRow.className = 'picker-actions';
        const setButton = document.createElement('button');
        setButton.type = 'button';
        setButton.className = 'btn btn-primary';
        setButton.textContent = 'Set';
        setButton.addEventListener('click', () => {
            const time = `${String(hourSpinner.getValue()).padStart(2, '0')}:${String(minuteSpinner.getValue()).padStart(2, '0')}`;
            input.value = time;
            closePopup(popup);
        });

        grid.appendChild(hourSpinner.element);
        grid.appendChild(minuteSpinner.element);
        actionRow.appendChild(setButton);
        grid.appendChild(actionRow);
    }

    timeInputs.forEach(input => {
        const popup = createPopup();
        popups.push(popup);

        input.addEventListener('focus', () => {
            buildTimePopup(popup, input);
            openPopup(popup, input);
        });

        input.addEventListener('click', () => {
            buildTimePopup(popup, input);
            openPopup(popup, input);
        });
    });

    document.addEventListener('click', (event) => {
        const target = event.target;
        const isInput = target.matches('.date-picker-input, .time-picker-input');
        const isPopup = target.closest('.picker-popup');

        if (!isInput && !isPopup) {
            popups.forEach(closePopup);
        }
    });
});