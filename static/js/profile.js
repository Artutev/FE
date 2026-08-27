document.addEventListener('DOMContentLoaded', () => {
    const moreEvents = document.getElementById('profileMoreEvents');
    const moreButton = document.getElementById('profileMoreButton');

    if (!moreEvents || !moreButton) return;

    moreButton.addEventListener('click', () => {
        const isVisible = moreEvents.classList.toggle('is-visible');
        moreButton.textContent = isVisible ? 'Свернуть' : 'Показать ещё';
    });
});