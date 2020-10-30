from django.contrib import admin
from .models import Post, Comment,Category,Contact,Watchlater,History


admin.site.register(Category)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user_from','user_to','created')



@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug','category', 'author','created','updated', 'publish', 'status')
    list_filter = ('status', 'created', 'publish', 'author','category')
    list_editable = ('slug','category', 'author', 'publish', 'status')
    search_fields = ('title', 'body','category')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'publish'
    ordering = ('status', 'publish')
    list_per_page = 5
    list_max_show_all = 8


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id','user','parent', 'post', 'created', 'active','reply_to')
    list_filter = ('active', 'created', 'updated')
    search_fields = ('user','parent','reply_to','body')
    list_editable = ('user','parent', 'post', 'active','reply_to')
    list_per_page = 5
    list_max_show_all = 8

# history 
@admin.register(Watchlater)
class WatchAdmin(admin.ModelAdmin):
    list_display = ('watch_id','user','post_watch_id')
    list_filter = ('watch_id','user','post_watch_id')
    search_fields= ('watch_id','user','post_watch_id')
    list_per_page = 5
    list_max_show_all = 8

# history
@admin.register(History)
class WatchAdmin(admin.ModelAdmin):
    list_display = ('hist_id','user','post_hist_id')
    list_filter = ('hist_id','user','post_hist_id')
    search_fields= ('hist_id','user','post_hist_id')
    list_per_page = 20
    list_max_show_all = 8
    


