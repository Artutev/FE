// Выбор места мероприятия: поиск адреса с подсказками, точка на карте,
// перетаскиваемая метка, «Я здесь».
// Подсказки по мере ввода — Photon (komoot, данные OpenStreetMap): он сделан для автодополнения.
// Nominatim такое запрещает правилами, поэтому он остался только запасным для «адрес по точке».
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
    const PHOTON = 'https://photon.komoot.io';
    // Photon знает только en/de/fr; «default» — местные названия (по-русски в России, по-чешски в Чехии)
    const PHOTON_LANG = lang === 'en' ? 'en' : 'default';
    const venueInput = document.querySelector('input[name="venue_name"]');
    const cityInput = document.querySelector('input[name="city"]');
    const countryInput = document.querySelector('input[name="country"]');

    // Город и страна — для фильтра афиши по городу (берём из ответа геокодера)
    function setPlaceMeta(place) {
        const a = (place && place.address) || {};
        if (cityInput) cityInput.value = (a.city || a.town || a.village || a.municipality || '').slice(0, 100);
        if (countryInput) countryInput.value = (a.country || '').slice(0, 100);
    }

    const T = {
        hint: etT('Начните вводить адрес или нажмите на карту, чтобы поставить точку.', 'Start typing an address or tap the map to drop a pin.', 'Začněte psát adresu nebo klepněte do mapy a umístěte špendlík.'),
        searching: etT('Ищем…', 'Searching…', 'Hledáme…'),
        nothing: etT('Ничего не нашли. Уточните запрос или поставьте точку на карте.', 'Nothing found. Refine the query or drop a pin on the map.', 'Nic nenalezeno. Upřesněte dotaz nebo umístěte špendlík do mapy.'),
        pinned: etT('Точка на карте выбрана — её можно перетащить.', 'Pin placed — you can drag it.', 'Špendlík umístěn — můžete ho přetáhnout.'),
        locating: etT('Определяем местоположение…', 'Getting your location…', 'Zjišťujeme polohu…'),
        geoError: etT('Не удалось определить местоположение. Разрешите доступ к геолокации.', "Couldn't get your location. Allow location access.", 'Nepodařilo se zjistit polohu. Povolte přístup k poloze.'),
        linkLooking: etT('Ищем точку по ссылке…', 'Reading the map link…', 'Hledáme bod podle odkazu…'),
        linkFailed: etT('Не получилось найти точку в этой ссылке. Введите адрес или поставьте точку на карте.', "Couldn't find a place in this link. Type the address or drop a pin.", 'V odkazu jsme bod nenašli. Zadejte adresu nebo umístěte špendlík.'),
        offline: etT('Сервис адресов недоступен. Точку можно поставить на карте вручную.', 'Address service is unavailable. You can still drop a pin manually.', 'Služba adres není dostupná. Špendlík můžete umístit ručně.'),
    };

    // ---------- Map ----------
    // Где открыть карту, если точки ещё нет: последнее место организатора → последняя точка в этом браузере →
    // город по часовому поясу → столица по языку. От центра зависят и подсказки адреса (ближние выше).
    const recentPlaces = (() => {
        const el = document.getElementById('recentPlaces');
        try { return el ? JSON.parse(el.textContent) : []; } catch (error) { return []; }
    })();
    const CENTER_KEY = 'et-map-center';
    const TZ_CITIES = {
        'Europe/Moscow': [55.7558, 37.6173], 'Europe/Kaliningrad': [54.7104, 20.4522], 'Europe/Samara': [53.1959, 50.1002],
        'Asia/Yekaterinburg': [56.8389, 60.6057], 'Asia/Novosibirsk': [55.0084, 82.9357], 'Asia/Krasnoyarsk': [56.0153, 92.8932],
        'Asia/Irkutsk': [52.2870, 104.3050], 'Asia/Vladivostok': [43.1155, 131.8855], 'Europe/Minsk': [53.9006, 27.5590],
        'Europe/Kyiv': [50.4501, 30.5234], 'Europe/Kiev': [50.4501, 30.5234], 'Asia/Almaty': [43.2389, 76.8897],
        'Asia/Qostanay': [53.2144, 63.6246], 'Asia/Aqtobe': [50.2839, 57.1670], 'Asia/Tashkent': [41.2995, 69.2401],
        'Asia/Bishkek': [42.8746, 74.5698], 'Asia/Tbilisi': [41.7151, 44.8271], 'Asia/Yerevan': [40.1792, 44.4991],
        'Asia/Baku': [40.4093, 49.8671], 'Europe/Prague': [50.0755, 14.4378], 'Europe/Bratislava': [48.1486, 17.1077],
        'Europe/Berlin': [52.5200, 13.4050], 'Europe/Vienna': [48.2082, 16.3738], 'Europe/Warsaw': [52.2297, 21.0122],
        'Europe/London': [51.5072, -0.1276], 'Europe/Riga': [56.9496, 24.1052], 'Europe/Vilnius': [54.6872, 25.2797],
        'Europe/Tallinn': [59.4370, 24.7536], 'Europe/Belgrade': [44.7866, 20.4489], 'Asia/Dubai': [25.2048, 55.2708],
        'Europe/Istanbul': [41.0082, 28.9784],
    };
    function initialCenter() {
        const last = recentPlaces.find((place) => place.lat != null && place.lon != null);
        if (last) return [[last.lat, last.lon], 12];
        try {
            const saved = JSON.parse(localStorage.getItem(CENTER_KEY) || 'null');
            if (Array.isArray(saved) && saved.length === 2) return [saved, 12];
        } catch (error) { /* нет доступа к хранилищу */ }
        let zone = '';
        try { zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (error) { /* старый браузер */ }
        if (TZ_CITIES[zone]) return [TZ_CITIES[zone], 11];
        return [lang === 'cs' ? [50.0755, 14.4378] : [55.7558, 37.6173], 10];
    }
    const [startCenter, startZoom] = initialCenter();
    const map = L.map(mapDiv, { scrollWheelZoom: false, zoomControl: true }).setView(startCenter, startZoom);
    window.etLocationMap = map; // форма прячет/показывает карту (онлайн-мероприятие) — пересчитать размер
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
        try { localStorage.setItem(CENTER_KEY, JSON.stringify([+lat.toFixed(4), +lon.toFixed(4)])); } catch (error) { /* не страшно */ }
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

    // Ответ Photon (GeoJSON) → тот же вид, что у Nominatim, чтобы formatPlace работал с обоими
    // Здание с собственным именем («Центральный телеграф») — тоже место, а улица или город — нет
    const NOT_A_VENUE = ['place', 'highway', 'boundary', 'landuse', 'railway'];
    function fromPhoton(feature) {
        const p = feature.properties || {};
        const [lon, lat] = feature.geometry.coordinates;
        const street = p.street || (p.osm_key === 'highway' ? p.name : '');
        return {
            lat,
            lon,
            name: p.name || '',
            venue: p.name && !NOT_A_VENUE.includes(p.osm_key) ? p.name : '',
            address: {
                road: street,
                house_number: p.housenumber,
                city: p.city || p.town || p.village,
                suburb: p.district || p.locality,
                country: p.country,
            },
            display_name: [p.name, street, p.city, p.country].filter(Boolean).join(', '),
        };
    }

    async function search(query) {
        const center = map.getCenter();
        const params = new URLSearchParams({
            q: query,
            limit: '6',
            lang: PHOTON_LANG,
            // ближе к тому, что видно на карте, — выше в списке
            lat: center.lat.toFixed(4),
            lon: center.lng.toFixed(4),
            zoom: String(Math.round(map.getZoom())),
        });
        const key = params.toString();
        if (cache.has(key)) return cache.get(key);
        if (searchController) searchController.abort();
        searchController = new AbortController();
        const response = await fetch(`${PHOTON}/api/?${key}`, { signal: searchController.signal });
        if (!response.ok) throw new Error('search failed');
        const results = ((await response.json()).features || []).map(fromPhoton);
        cache.set(key, results);
        return results;
    }

    async function reverse(lat, lon) {
        try {
            const params = new URLSearchParams({ lat, lon, lang: PHOTON_LANG, limit: '1' });
            const response = await fetch(`${PHOTON}/reverse?${params}`);
            if (!response.ok) throw new Error('photon reverse failed');
            const feature = ((await response.json()).features || [])[0];
            if (feature) return fromPhoton(feature);
        } catch (error) { /* запасной вариант ниже */ }
        // Один запрос на клик/перетаскивание — это Nominatim разрешает
        const params = new URLSearchParams({
            format: 'jsonv2', addressdetails: '1', zoom: '18', 'accept-language': lang, lat, lon,
        });
        const response = await fetch(`${NOMINATIM}/reverse?${params}`);
        if (!response.ok) throw new Error('reverse failed');
        return response.json();
    }

    async function fillFromPoint(lat, lon) {
        // Город уточняем всегда, а текст адреса — только если его не писали руками (например, «Лофт Крыша»)
        const keepText = input.value.trim() && !autoFilled;
        try {
            const place = await reverse(lat, lon);
            if (place && !place.error) {
                setPlaceMeta(place);
                if (!keepText) {
                    input.value = formatPlace(place).value;
                    autoFilled = true;
                }
            }
        } catch (error) {
            if (!keepText) setStatus(T.offline, true);
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
        setPlaceMeta(place);
        // Выбрали заведение («Кафе Пушкин») — подставим его в «Название места», а в адрес — улицу и город
        if (place.venue && venueInput && !venueInput.value.trim()) {
            venueInput.value = place.venue;
            const a = place.address || {};
            const street = [a.road, a.house_number].filter(Boolean).join(' ');
            const rest = [street, a.city].filter(Boolean).join(', ');
            if (rest) input.value = rest;
        }
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

    // ---------- Ссылка из Яндекс / Google / 2ГИС / Mapy.cz вместо адреса ----------
    const mapLinkUrl = picker.dataset.mapLinkUrl;
    const looksLikeLink = (text) => /^https?:\/\/\S+$/i.test(text);
    async function useMapLink(link) {
        closeSuggest();
        picker.classList.add('is-loading');
        setStatus(T.linkLooking);
        try {
            const response = await fetch(`${mapLinkUrl}?${new URLSearchParams({ url: link })}`, {
                headers: { 'X-Requested-With': 'fetch' },
            });
            if (!response.ok) throw new Error('not found');
            const place = await response.json();
            if (place.venue && venueInput && !venueInput.value.trim()) venueInput.value = place.venue;
            input.value = '';
            autoFilled = true;
            placePin(place.lat, place.lon, { zoom: 17 });
            await fillFromPoint(place.lat, place.lon);
        } catch (error) {
            setStatus(T.linkFailed, true);
        } finally {
            picker.classList.remove('is-loading');
        }
    }

    // ---------- Мои места ----------
    document.querySelectorAll('.loc-recent-chip').forEach((chip) => {
        chip.addEventListener('click', () => {
            const place = recentPlaces[Number(chip.dataset.placeIndex)];
            if (!place) return;
            if (venueInput) venueInput.value = place.venue || '';
            input.value = place.address || '';
            if (cityInput) cityInput.value = place.city || '';
            if (countryInput) countryInput.value = place.country || '';
            autoFilled = false; // это текст организатора — не затираем при перетаскивании метки
            closeSuggest();
            if (place.lat != null && place.lon != null) placePin(place.lat, place.lon, { zoom: 17 });
            else clearPin();
        });
    });

    let typingTimer = null;
    input.addEventListener('input', () => {
        autoFilled = false;
        clearTimeout(typingTimer);
        const query = input.value.trim();
        if (looksLikeLink(query)) {
            useMapLink(query);
            return;
        }
        if (!marker) setPlaceMeta(null); // адрес без точки — город неизвестен, не оставляем старый
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
