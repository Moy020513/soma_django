from django import template

register = template.Library()

@register.simple_tag
def reorder_admin_apps(app_list):
    """Return a reordered list of admin apps where 'recursos_humanos' is placed at index 1.

    Keeps the original relative order of other apps. If the app isn't present
    the original list is returned unchanged.
    """
    try:
        apps = list(app_list)
    except Exception:
        return app_list

    target = None
    for app in apps:
        if getattr(app, 'app_label', None) == 'recursos_humanos':
            target = app
            break
    if target:
        # remove and insert at second position (index 1)
        try:
            apps.remove(target)
            insert_at = 1 if len(apps) >= 1 else len(apps)
            apps.insert(insert_at, target)
        except ValueError:
            pass
    return apps
