from celery.schedules import crontab


DEFAULT_LOAN_PERIOD = 28    # in days

CHECKER_CELERYBEAT_SCHEDULE = {
    'checker-beat': {
        'task': 'invenio.modules.circulation.tasks.detect_overdue',
        'schedule': crontab(minute='*/1'),
    }
}

CELERYBEAT_SCHEDULE = CHECKER_CELERYBEAT_SCHEDULE
