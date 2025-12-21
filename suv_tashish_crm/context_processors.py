def language_context(request):
    """Provide translations dict `T`, current language code `current_lang`, and language options.

    Languages supported: 'uz_lat', 'uz_cyrl', 'ru'.
    """
    import os, json
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locale_dir = os.path.join(BASE_DIR, 'locale')
    lang = request.session.get('lang', 'uz_lat')
    # clamp to known values
    if lang not in ('uz_lat', 'uz_cyrl', 'ru'):
        lang = 'uz_lat'
    filename = os.path.join(locale_dir, f"{lang}.json")
    translations = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except Exception:
        translations = {}
    # expose small mapping and current lang
    return {'T': translations, 'current_lang': lang, 'LANG_OPTIONS': [('uz_lat','Uzbek - Lotin'), ('uz_cyrl','Uzbek - Кирил'), ('ru','Русский')]}
