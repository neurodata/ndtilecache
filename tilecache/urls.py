from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('tilecache.views',
    # everything matches the tile cache
    url(r'^(?P<webargs>.*)$', 'getTile'),
)
