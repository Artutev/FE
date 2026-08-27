document.addEventListener('DOMContentLoaded', () => {
    const eventTypeField = document.getElementById('id_event_type');
    const locationField = document.getElementById('id_location');
    const weddingFields = document.querySelectorAll('.wedding-only');
    const weddingHint = document.getElementById('weddingHint');

    function updateWeddingFields() {
        const showWedding = eventTypeField && eventTypeField.value === 'wedding';
        weddingFields.forEach(field => {
            field.style.display = showWedding ? 'block' : 'none';
        });

        if (weddingHint) {
            weddingHint.style.display = showWedding ? 'none' : 'block';
        }

        if (locationField) {
            locationField.required = eventTypeField && eventTypeField.value !== 'other';
        }
    }

    if (eventTypeField) {
        eventTypeField.addEventListener('change', updateWeddingFields);
        updateWeddingFields();
    }
});
