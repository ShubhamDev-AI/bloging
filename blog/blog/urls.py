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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('account.urls')),
    path('posts/', include('posts.urls')),
    path('social-auth/',include('social_django.urls', namespace='social')),
    path('inbox/notifications/',include(notifications.urls,namespace='notifications')), 
    path('notice/',include('notice.urls',namespace='notice')), 

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
            name='django.contrib.sitemaps.views.sitemap'),
    path('', include('pwa.urls'))

]
if settings.DEBUG:
     urlpatterns += static(settings.MEDIA_URL,
 document_root=settings.MEDIA_ROOT)

