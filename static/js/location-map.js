// Выбор места мероприятия: поиск адреса с подсказками, точка на карте,
// перетаскиваемая метка, «Я здесь». Геокодер — OpenStreetMap Nominatim.
document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('locPicker');
    const input = document.querySelector('input[name="location"]');
    const mapDiv = document.getElementById('locationMap');
    const latInput = document.querySelector('input[name="latitude"]');
    const lonInput = document.querySelector('input[name="longitude"]');
    if (!picker || !input || !mapDiv || typeof L === 'undefined') return;

    const suggestList = document.getElementById('locSuggest');
    const statusEl = document.getElementById('locStatus');
    const clearPointBtn = document.getElementById('locClearPoint');
    const geoBtn = document.getElementById('locGeo');
    const lang = window.etLang || 'ru';
    const NOMINATIM = 'https://nominatim.openstreetmap.org';

    const T = {
        hint: etT('Начните вводить адрес или нажмите на карту, чтобы поставить точку.', 'Start typing an address or tap the map to drop a pin.', 'Začněte psát adresu nebo klepněte do mapy a umístěte špendlík.'),
        searching: etT('Ищем…', 'Searching…', 'Hledáme…'),
        nothing: etT('Ничего не нашли. Уточните запрос или поставьте точку на карте.', 'Nothing found. Refine the query or drop a pin on the map.', 'Nic nenalezeno. Upřesněte dotaz nebo umístěte špendlík do mapy.'),
        pinned: etT('Точка на карте выбрана — её можно перетащить.', 'Pin placed — you can drag it.', 'Špendlík umístěn — můžete ho přetáhnout.'),
        locating: etT('Определяем местоположение…', 'Getting your location…', 'Zjišťujeme polohu…'),
        geoError: etT('Не удалось определить местоположение. Разрешите доступ к геолокации.', "Couldn't get your location. Allow location access.", 'Nepodařilo se zjistit polohu. Povolte přístup k poloze.'),
        offline: etT('Сервис адресов недоступен. Точку можно поставить на карте вручную.', 'Address service is unavailable. You can still drop a pin manually.', 'Služba adres není dostupná. Špendlík můžete umístit ručně.'),
    };

    // ---------- Map ----------
    const DEFAULT_CENTER = lang === 'cs' ? [50.0755, 14.4378] : [43.2389, 76.8897];
    const map = L.map(mapDiv, { scrollWheelZoom: false, zoomControl: true }).setView(DEFAULT_CENTER, 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            // OSM требует Referer с адресом сайта, иначе отдаёт 403 «Access blocked»
            referrerPolicy: 'strict-origin-when-cross-origin',
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    // Колесо мыши включаем только после клика по карте, чтобы страница нормально скроллилась
    map.on('focus click', () => map.scrollWheelZoom.enable());
    map.on('blur', () => map.scrollWheelZoom.disable());

    const pinIcon = L.divIcon({
        className: 'loc-pin',
        html: '<span></span>',
        iconSize: [32, 42],
        iconAnchor: [16, 40],
    });

    let marker = null;
    let autoFilled = false; // текст в поле подставлен скриптом, а не набран вручную

    function setStatus(text, isError = false) {
        statusEl.textContent = text;
        statusEl.classList.toggle('is-error', isError);
    }

    function setCoords(lat, lon) {
        latInput.value = Number(lat).toFixed(6);
        lonInput.value = Number(lon).toFixed(6);
        clearPointBtn.hidden = false;
    }

    function placePin(lat, lon, { zoom = 16, pan = true } = {}) {
        if (!marker) {
            marker = L.marker([lat, lon], { draggable: true, icon: pinIcon, autoPan: true }).addTo(map);
            marker.on('dragend', () => {
                const pos = marker.getLatLng();
                setCoords(pos.lat, pos.lng);
                fillFromPoint(pos.lat, pos.lng);
            });
        } else {
            marker.setLatLng([lat, lon]);
        }
        setCoords(lat, lon);
        if (pan) map.setView([lat, lon], Math.max(map.getZoom(), zoom));
        setStatus(T.pinned);
    }

    function clearPin() {
        if (marker) marker.remove();
        marker = null;
        latInput.value = '';
        lonInput.value = '';
        clearPointBtn.hidden = true;
        setStatus(T.hint);
    }

    // ---------- Address formatting ----------
    function formatPlace(place) {
        const a = place.address || {};
        const street = [a.road || a.pedestrian || a.footway || a.square, a.house_number].filter(Boolean).join(' ');
        const city = a.city || a.town || a.village || a.municipality || a.county || '';
        const name = place.name && place.name !== street && place.name !== city ? place.name : '';
        const primary = name || street || city || (place.display_name || '').split(',')[0];
        const secondaryParts = [name ? street : '', a.suburb || a.city_district, city !== primary ? city : '', a.country]
            .filter((part) => part && part !== primary);
        const secondary = [...new Set(secondaryParts)].join(', ');
        const value = [primary, name ? street : '', city !== primary ? city : ''].filter(Boolean).join(', ');
        return { primary, secondary, value };
    }

    // ---------- Geocoding ----------
    let searchController = null;
    const cache = new Map();

    async function search(query) {
        const bounds = map.getBounds();
        const params = new URLSearchParams({
            format: 'jsonv2',
            addressdetails: '1',
            limit: '6',
            'accept-language': lang,
            q: query,
            viewbox: [bounds.getWest(), bounds.getNorth(), bounds.getEast(), bounds.getSouth()].join(','),
        });
        const key = params.toString();
        if (cache.has(key)) return cache.get(key);
        if (searchController) searchController.abort();
        searchController = new AbortController();
        const response = await fetch(`${NOMINATIM}/search?${key}`, { signal: searchController.signal });
        if (!response.ok) throw new Error('search failed');
        const results = await response.json();
        cache.set(key, results);
        return results;
    }

    async function reverse(lat, lon) {
        const params = new URLSearchParams({
            format: 'jsonv2', addressdetails: '1', zoom: '18', 'accept-language': lang, lat, lon,
        });
        const response = await fetch(`${NOMINATIM}/reverse?${params}`);
        if (!response.ok) throw new Error('reverse failed');
        return response.json();
    }

    async function fillFromPoint(lat, lon) {
        // Не затираем то, что пользователь написал сам (например, «Лофт Крыша»)
        if (input.value.trim() && !autoFilled) return;
        try {
            const place = await reverse(lat, lon);
            if (place && !place.error) {
                input.value = formatPlace(place).value;
                autoFilled = true;
            }
        } catch (error) {
            setStatus(T.offline, true);
        }
    }

    // ---------- Suggestions dropdown ----------
    let items = [];
    let activeIndex = -1;

    function closeSuggest() {
        suggestList.hidden = true;
        suggestList.innerHTML = '';
        items = [];
        activeIndex = -1;
        input.setAttribute('aria-expanded', 'false');
    }

    function highlight(index) {
        activeIndex = index;
        [...suggestList.children].forEach((li, i) => {
            li.classList.toggle('is-active', i === index);
            li.setAttribute('aria-selected', String(i === index));
        });
        if (index >= 0) input.setAttribute('aria-activedescendant', `locOpt${index}`);
        else input.removeAttribute('aria-activedescendant');
    }

    function choose(index) {
        const place = items[index];
        if (!place) return;
        const formatted = formatPlace(place);
        input.value = formatted.value;
        autoFilled = true;
        placePin(parseFloat(place.lat), parseFloat(place.lon), { zoom: 17 });
        closeSuggest();
    }

    function renderSuggest(results) {
        items = results;
        suggestList.innerHTML = '';
        if (!results.length) {
            closeSuggest();
            setStatus(T.nothing);
            return;
        }
        results.forEach((place, index) => {
            const { primary, secondary } = formatPlace(place);
            const li = document.createElement('li');
            li.id = `locOpt${index}`;
            li.setAttribute('role', 'option');
            li.innerHTML = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg><span><strong></strong><em></em></span>';
            li.querySelector('strong').textContent = primary;
            li.querySelector('em').textContent = secondary;
            li.addEventListener('mousedown', (event) => {
                event.preventDefault(); // не терять фокус до выбора
                choose(index);
            });
            suggestList.appendChild(li);
        });
        suggestList.hidden = false;
        input.setAttribute('aria-expanded', 'true');
        highlight(-1);
        setStatus(marker ? T.pinned : T.hint);
    }

    input.setAttribute('autocomplete', 'off');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', 'locSuggest');
    input.setAttribute('aria-expanded', 'false');

    let typingTimer = null;
    input.addEventListener('input', () => {
        autoFilled = false;
        clearTimeout(typingTimer);
        const query = input.value.trim();
        if (query.length < 3) {
            closeSuggest();
            picker.classList.remove('is-loading');
            return;
        }
        typingTimer = setTimeout(async () => {
            picker.classList.add('is-loading');
            setStatus(T.searching);
            try {
                renderSuggest(await search(query));
            } catch (error) {
                if (error.name !== 'AbortError') setStatus(T.offline, true);
            } finally {
                picker.classList.remove('is-loading');
            }
        }, 450);
    });

    input.addEventListener('keydown', (event) => {
        if (suggestList.hidden || !items.length) return;
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            highlight((activeIndex + 1) % items.length);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            highlight((activeIndex - 1 + items.length) % items.length);
        } else if (event.key === 'Enter') {
            event.preventDefault(); // не отправлять форму
            choose(activeIndex >= 0 ? activeIndex : 0);
        } else if (event.key === 'Escape') {
            closeSuggest();
        }
    });

    input.addEventListener('blur', () => setTimeout(closeSuggest, 150));

    // ---------- Map interactions ----------
    map.on('click', (event) => {
        const { lat, lng } = event.latlng;
        placePin(lat, lng, { pan: false });
        fillFromPoint(lat, lng);
    });

    clearPointBtn.addEventListener('click', clearPin);

    if (geoBtn) {
        if (!('geolocation' in navigator)) {
            geoBtn.hidden = true;
        } else {
            geoBtn.addEventListener('click', () => {
                setStatus(T.locating);
                geoBtn.disabled = true;
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        geoBtn.disabled = false;
                        const { latitude, longitude } = position.coords;
                        placePin(latitude, longitude, { zoom: 17 });
                        fillFromPoint(latitude, longitude);
                    },
                    () => {
                        geoBtn.disabled = false;
                        setStatus(T.geoError, true);
                    },
                    { enableHighAccuracy: true, timeout: 10000 }
                );
            });
        }
    }

    // ---------- Initial state (edit form / validation errors) ----------
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
        placePin(lat, lon, { zoom: 16 });
    } else {
        setStatus(T.hint);
    }

    // Карта могла инициализироваться в скрытом/узком контейнере
    setTimeout(() => map.invalidateSize(), 200);
});
