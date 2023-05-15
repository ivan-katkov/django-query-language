DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    # 'tests.models.MainModel',
    # 'tests.models.RelatedModel',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'querylanguage',
    'tests',
)

# MIDDLEWARE = []

# #ROOT_URLCONF = 'tests.urls'

USE_TZ = True

# SECRET_KEY = 'topsecret'

# TEMPLATES = [{
#     'BACKEND': 'django.template.backends.django.DjangoTemplates',
#     'APP_DIRS': True,
# }]


# STATIC_URL = '/static/'
