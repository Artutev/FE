// Афиша на карте: метки мероприятий (объединяются при отдалении) и «Рядом со мной».
document.addEventListener('DOMContentLoaded', () => {
    const mapDiv = document.getElementById('eventsMap');
    const dataEl = document.getElementById('eventsMapData');
    if (!mapDiv || !dataEl || typeof L === 'undefined') return;

    let points = [];
    try { points = JSON.parse(dataEl.textContent) || []; } catch (error) { points = []; }

    const map = L.map(mapDiv, { scrollWheelZoom: false }).setView([55.7558, 37.6173], 4);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        referrerPolicy: 'strict-origin-when-cross-origin',
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    map.on('focus click', () => map.scrollWheelZoom.enable());
    map.on('blur', () => map.scrollWheelZoom.disable());

    const pin = L.divIcon({ className: 'loc-pin', html: '<span></span>', iconSize: [32, 42], iconAnchor: [16, 40], popupAnchor: [0, -36] });
    const group = typeof L.markerClusterGroup === 'function'
        ? L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 50 })
        : L.featureGroup();

    // Подпись метки — только через textContent (названия пишут пользователи)
    function popup(point) {
        const box = document.createElement('div');
        box.className = 'events-map-popup';
        const link = document.createElement('a');
        link.href = point.url;
        link.textContent = point.name;
        box.appendChild(link);
        [point.when, point.place].filter(Boolean).forEach((text) => {
            const line = document.createElement('span');
            line.textContent = text;
            box.appendChild(line);
        });
        return box;
    }

    points.forEach((point) => {
        L.marker([point.lat, point.lon], { icon: pin, title: point.name }).bindPopup(popup(point)).addTo(group);
    });
    group.addTo(map);
    if (points.length) map.fitBounds(group.getBounds().pad(0.2), { maxZoom: 14 });

    // ---------- Рядом со мной ----------
    const nearBtn = document.getElementById('nearMe');
    const note = document.getElementById('eventsMapNote');
    let me = null;
    if (nearBtn) {
        if (!('geolocation' in navigator)) {
            nearBtn.hidden = true;
        } else {
            nearBtn.addEventListener('click', () => {
                nearBtn.disabled = true;
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        nearBtn.disabled = false;
                        const here = [position.coords.latitude, position.coords.longitude];
                        if (me) me.setLatLng(here);
                        else me = L.circleMarker(here, { radius: 8, color: '#fff', weight: 3, fillColor: '#2563eb', fillOpacity: 1 }).addTo(map);
                        // Ближайшие мероприятия: подстраиваем масштаб так, чтобы попали до трёх ближайших
                        const nearest = points
                            .map((p) => ({ p, d: map.distance(here, [p.lat, p.lon]) }))
                            .sort((a, b) => a.d - b.d)
                            .slice(0, 3);
                        if (nearest.length) {
                            const bounds = L.latLngBounds([here, ...nearest.map(({ p }) => [p.lat, p.lon])]);
                            map.fitBounds(bounds.pad(0.25), { maxZoom: 15 });
                            const km = nearest[0].d / 1000;
                            if (note) {
                                note.textContent = etT('Ближайшее мероприятие — в ', 'The nearest event is ', 'Nejbližší akce je ')
                                    + (km < 1 ? `${Math.round(nearest[0].d)} ${etT('м', 'm', 'm')}` : `${km.toFixed(km < 10 ? 1 : 0)} ${etT('км', 'km', 'km')}`)
                                    + etT(' от вас.', ' away.', ' od vás.');
                            }
                        } else {
                            map.setView(here, 13);
                        }
                    },
                    () => {
                        nearBtn.disabled = false;
                        if (note) note.textContent = etT('Не удалось определить местоположение. Разрешите доступ к геолокации.', "Couldn't get your location. Allow location access.", 'Nepodařilo se zjistit polohu. Povolte přístup k poloze.');
                    },
                    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
                );
            });
        }
    }
});
