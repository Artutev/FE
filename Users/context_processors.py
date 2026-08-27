def current_language(request):
    language = request.session.get('language', 'ru')
    alternate = 'en' if language == 'ru' else 'ru'
    alternate_label = 'English' if language == 'ru' else 'Русский'
    return {
        'LANGUAGE_CODE': language,
        'current_language': language,
        'alternate_language': alternate,
        'alternate_language_label': alternate_label,
    }
