document.addEventListener('DOMContentLoaded', () => {
    const locationInput = document.querySelector('input[name="location"]');
    const mapDiv = document.getElementById('locationMap');
    const mapNotice = document.querySelector('.location-map-hint');

    if (!locationInput || !mapDiv || !mapNotice || typeof L === 'undefined') {
        return;
    }

    // Initialize Leaflet map
    const map = L.map(mapDiv).setView([55.75, 37.62], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let marker = null;
    const latInput = document.querySelector('input[name="latitude"]');
    const lonInput = document.querySelector('input[name="longitude"]');

    function setMarker(lat, lon, label) {
        if (marker) marker.remove();
        marker = L.marker([lat, lon]).addTo(map);
        if (label) marker.bindPopup(label).openPopup();
        map.setView([lat, lon], 15);
        if (latInput) latInput.value = lat;
        if (lonInput) lonInput.value = lon;
    }

    async function reverseGeocode(lat, lon) {
        try {
            const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`);
            if (!resp.ok) return null;
            const data = await resp.json();
            return data.display_name || null;
        } catch (e) {
            return null;
        }
    }

    async function searchAddress(query) {
        try {
            const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&q=${encodeURIComponent(query)}`);
            if (!resp.ok) return null;
            const results = await resp.json();
            return results && results.length ? results[0] : null;
        } catch (e) {
            return null;
        }
    }

    // Click on map to pick location
    map.on('click', async (e) => {
        const { lat, lng } = e.latlng;
        const addr = await reverseGeocode(lat, lng);
        if (addr) {
            locationInput.value = addr;
            mapNotice.textContent = etT('Адрес установлен на основе выбора на карте.', 'Address set from the map selection.', 'Adresa byla nastavena podle výběru na mapě.');
            setMarker(lat, lng, addr);
        } else {
            mapNotice.textContent = etT('Не удалось получить адрес для выбранной точки.', "Couldn't get an address for this point.", 'Pro tento bod se nepodařilo zjistit adresu.');
            setMarker(lat, lng, null);
        }
    });

    // When user types an address, search and move map
    let typingTimer = null;
    locationInput.addEventListener('input', () => {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(async () => {
            const q = locationInput.value.trim();
            if (!q) return;
            mapNotice.textContent = etT('Ищем адрес...', 'Searching for the address...', 'Hledáme adresu...');
            const res = await searchAddress(q);
            if (res) {
                setMarker(res.lat, res.lon, res.display_name || q);
                mapNotice.textContent = etT('Найдено и отмечено на карте.', 'Found and marked on the map.', 'Nalezeno a označeno na mapě.');
            } else {
                mapNotice.textContent = etT('Адрес не найден. Попробуйте уточнить запрос.', 'Address not found. Try a more specific query.', 'Adresa nenalezena. Zkuste upřesnit dotaz.');
            }
        }, 600);
    });

    // If input already has value on load, try to find it
    (async () => {
        // If form already contains latitude/longitude, use them first
        const latVal = latInput && latInput.value ? parseFloat(latInput.value) : null;
        const lonVal = lonInput && lonInput.value ? parseFloat(lonInput.value) : null;
        if (latVal && lonVal) {
            setMarker(latVal, lonVal, locationInput.value || null);
            return;
        }
        const q = locationInput.value.trim();
        if (!q) return;
        const res = await searchAddress(q);
        if (res) setMarker(res.lat, res.lon, res.display_name || q);
    })();
});
