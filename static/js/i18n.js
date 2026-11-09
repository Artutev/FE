// Мини-переводчик для JS. Язык страницы задаётся в base.html (window.ET_LANG).
(function () {
    var lang = window.ET_LANG || document.documentElement.lang || 'ru';

    window.etT = function (ru, en, cs) {
        if (lang === 'en') return en;
        if (lang === 'cs') return cs || en;
        return ru;
    };

    window.etLang = lang;
    window.etLocale = { ru: 'ru-RU', en: 'en-GB', cs: 'cs-CZ' }[lang] || 'ru-RU';
})();
