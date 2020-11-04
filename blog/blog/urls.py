import debug_toolbar
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from posts.sitemaps import PostSitemap
import  notifications.urls


sitemaps = {
    'posts': PostSitemap,
}

from django.conf.urls import (
    handler400, handler403, handler404, handler500
)
handler400 = 'posts.views.handler400'
handler403 = 'posts.views.handler403'
handler404 = 'posts.views.handler404'
handler500 = 'posts.views.handler500'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('account.urls')),
    path('posts/', include('posts.urls')),
    path('social-auth/',include('social_django.urls', namespace='social')),
    path('inbox/notifications/',include(notifications.urls,namespace='notifications')), 
    path('notice/',include('notice.urls',namespace='notice')), 

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
            name='django.contrib.sitemaps.views.sitemap'),
    path('', include('pwa.urls')),
    path('__debug__/', include(debug_toolbar.urls)),


]
if settings.DEBUG:
     urlpatterns += static(settings.MEDIA_URL,
 document_root=settings.MEDIA_ROOT)

