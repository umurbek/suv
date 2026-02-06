def language_context(request):
    """Provide translations dict `T`, current language code `current_lang`, and language options.

    Languages supported: 'uz_lat', 'uz_cyrl', 'ru', 'en'.
    """
    import os, json
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locale_dir = os.path.join(BASE_DIR, 'locale')
    lang = request.session.get('lang', 'uz_lat')
    # clamp to known values
    if lang not in ('uz_lat', 'uz_cyrl', 'ru', 'en'):
        lang = 'uz_lat'
    filename = os.path.join(locale_dir, f"{lang}.json")
    translations = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except Exception:
        translations = {}
    # expose small mapping and current lang
    return {
        'T': translations,
        'current_lang': lang,
        'LANG_OPTIONS': [
            ('uz_lat', 'Uzbek - Latin'),
            ('uz_cyrl', 'Uzbek - Кирил'),
            ('ru', 'Русский'),
            ('en', 'English'),
        ],
    }


def google_maps_key(request):
    """Expose `GOOGLE_MAPS_API_KEY` to templates as `GOOGLE_MAPS_API_KEY`.

    This reads the value from Django settings so it can be configured via
    environment variable in production.
    """
    try:
        from django.conf import settings
        return {'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')}
    except Exception:
        return {'GOOGLE_MAPS_API_KEY': ''}


def admin_login_error(request):
    """Pop a one-time admin login error from session and expose to templates.

    This ensures admin auth errors can be shown inside admin pages only
    by setting `request.session['admin_login_error']` from the login view.
    """
    try:
        msg = request.session.pop('admin_login_error')
        return {'admin_login_error': msg}
    except Exception:
        return {'admin_login_error': None}
