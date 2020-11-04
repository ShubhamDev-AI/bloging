from django.urls import path, include
from . import views
from .feeds import LatestPostsFeed
from django_filters.views import FilterView
from django.views.generic import TemplateView
from django.conf.urls import url
from .filters import UserFilter
from .views import UpdatePostView,DeletePostView,AddCategoryView,DetailPostView
from django.conf.urls import handler404,handler500

app_name = 'posts'

urlpatterns = [
    
    path('', views.post_list, name='post_list'),
    url('details/(?P<pk>\d+)/$', DetailPostView.as_view(), name='post_detail'),
    path('<int:post_id>/share/', views.post_share, name='post_share'),
    path('feed/', LatestPostsFeed(), name='post_feed'),
    path('search/', views.post_search, name='post_search'),
    path('searchuser/', views.search, name='search'),
    url(r'^searching/$', FilterView.as_view(filterset_class=UserFilter,
        template_name='posts/post/user_filter.html'), name='searching'),

    path('post-upload/', views.post_upload, name='post-upload'),
    path('<int:pk>/update/',UpdatePostView.as_view(),name='update_post'),
    path('<int:pk>/delete/',DeletePostView.as_view(),name='delete_post'),
    path('add_category/',AddCategoryView.as_view(),name='add-category'),
    path('category/<str:cats>/',views.CategoryView,name='category'),
    path('politics/',views.PoliticsView,name='politics'),
    path('users/', views.user_list, name='user_list'),
    path('users/follow/', views.user_follow, name='user_follow'),
    path('users/<username>/', views.user_detail, name='user_detail'),
    path('user_activity/', views.user_activity, name='user_activity'),
    path('post-comment/<int:post_id>', views.post_comment, name='post_comment'),
    path('post-comment/<int:post_id>/<int:parent_comment_id>', views.post_comment, name='comment_reply'),
    path('increase-likes/<int:id>/', views.IncreaseLikesView.as_view(), name='increase_likes'),
    path('likes/<int:pk>/', views.LikeView, name='like_post'),
    path('dislikes/<int:pk>/',views.DisLikeView,name='dislike_post'),
    # history watch later
    path('watchlater', views.watchlater, name='watchlater'),
    path('history', views.history, name='history'),
    path('history/delete/<int:id>/',views.DeleteHistory, name='history_delete'),
    path('history/delete/post/<int:id>/<int:user>',views.DeletePerHistory, name='history_Per_delete'),
    path('watchlater/delete/<int:id>/',views.DeleteWatchLater, name='watchlater_delete'),
    path('watchlater/delete/post/<int:id>/<int:user>',views.DeletePerWatchLater, name='watchlater_Per_delete'),
    path('blocked',views.BlockedUser, name='blocked'),
    path('timeline',views.TimeLine, name='timeline'),
    path('pie-chart/', views.pie_chart, name='pie-chart'),
    path('posttranding/<str:trend>/',views.trendingpost,name="post_trend"),
    url('^followers/(?P<username>[\w-]+)/$',views.followers,name="friendship_followers"),
    url('^following/(?P<username>[\w-]+)/$',views.following,name="friendship_following"),
    url(
        "^follower/remove/(?P<followee_username>[\w-]+)/$",
        views.follower_remove,
        name="follower_remove",
    ),
    url(
        "^blockers/(?P<username>[\w-]+)/$",
        views.blockers,
        name="friendship_blockers",
    ),
    url(
        "^blocking/(?P<username>[\w-]+)/$",
        views.blocking,
        name="friendship_blocking",
    ),
    url(
        "^block/add/(?P<blocked_username>[\w-]+)/$",
        views.block_add,
        name="block_add",
    ),
    url(
        "^block/remove/(?P<blocked_username>[\w-]+)/$",
        views.block_remove,
        name="block_remove",
    ),
    path('users/block/user/', views.block_unblock, name='block_unblock'),
    url(r'^ajax_calls/search/', views.autocompleteModel,name="ajax_autocomplete"),



]
handler404 = views.handler404
handler500 = views.handler500
