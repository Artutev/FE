from Users.i18n import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, get_language


def current_language(request):
    language = get_language(request)
    return {
        'LANGUAGE_CODE': language,
        'current_language': language,
        'current_language_label': LANGUAGE_LABELS[language],
        'available_languages': [
            (code, LANGUAGE_LABELS[code]) for code in SUPPORTED_LANGUAGES
        ],
    }
