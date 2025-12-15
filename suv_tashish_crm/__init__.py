try:
	# import signals so handlers are registered when Django starts
	from . import signals  # noqa: F401
except Exception:
	# avoid import-time errors in environments where Django isn't fully configured
	pass
