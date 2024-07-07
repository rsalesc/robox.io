from robox.box import package


def clear_package_cache():
    pkgs = [package]

    for pkg in pkgs:
        for fn in pkg.__dict__.values():
            if hasattr(fn, 'cache_clear'):
                fn.cache_clear()
