from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage,\
                                  PageNotAnInteger
from django.core.mail import send_mail
from django.views.generic import ListView
from django.shortcuts import redirect
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
from .models import *
from account.models import Profile
from .forms import EmailPostForm, CommentForm, SearchForm
from taggit.models import Tag
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, UserRegistrationForm, \
                   UserEditForm,PostForm
# filter
from django.contrib.auth.models import User
from .filters import UserFilter

# like 
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

# update post
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import  DetailView
from django.views.generic import ListView,UpdateView,DeleteView,CreateView
from django.urls import reverse_lazy,reverse
from common.decorators import ajax_required
# action
from actions.utils import create_action
from actions.models import Action
import markdown
from django.db.models import Q
# history watchlater
from django.db.models import Case, When
# blocked user
from account.models import Blocked
# notify
from  notifications.signals  import  notify 
# trending
from datetime import datetime,timedelta
now = datetime.now().strftime("%Y-%m-%d %H:%M")
today = datetime.today()
long_ago = today + timedelta(days=-30)
long_ago_timeline = today + timedelta(days=-15)

import numpy as np 
from django.contrib.auth.models import User

# -------------- trending algorithm ---------------------------------------
def trendingpostfunction():
    rdata = Post.objects.filter(publish__gte=long_ago)
    likerate = []
    dislikerate = []
    viewrate = []
    for i in rdata:
        lr = i.total_likes() + 1
        vr = i.total_views + 1
        lr = lr / vr
        likerate.append(lr)
        dr = i.total_dislikes() + 1
        dr = dr / vr
        dislikerate.append(dr)
        u = User.objects.count()
        vrt = vr / u
        viewrate.append(vrt)
    lr1 = np.array(likerate)
    dr1 = np.array(dislikerate)
    vr1 = np.array(viewrate)
    lr = lr1.round(2)
    dr = dr1.round(2)
    vr = vr1.round(2)
    results = []
    for i in lr, dr, vr:
        a = (lr - dr) + vr
        a = a * 50
    rdata = Post.objects.filter(publish__gte=long_ago)
    trendingdata = a
    j = 0
    trendingdict = {}
    for i in rdata:
        trendingdict[i.title] = trendingdata[j]
        j += 1
    trend = {k: v for k, v in sorted(trendingdict.items(), key=lambda item: item[1], reverse=True)}
    print('latest trending --', trend)
    trendlist = []
    for k in trend.keys():
        trendlist.append(k)
    print('trendlist --', trendlist)
    return trendlist
    # return HttpResponse('done')
# -----------------------------------------------------------------------------
def search(request):
    user_list = User.objects.all()
    user_filter = UserFilter(request.GET, queryset=user_list)
    return render(request, 'account/user_filter.html', {'filter': user_filter})

# @login_required
def post_list(request):
    latesttrend = trendingpostfunction()
    trendingwithdata = []
    temp =1
    for i in latesttrend:
        obj = Post.objects.get(title=i)
        trendingwithdata.append(obj)
        temp +=1
    trenddouble = trendingwithdata[:2]
    trendfour = trendingwithdata[2:7]
    print(trenddouble)
    print(trendfour)

    search = request.GET.get('search')
    order = request.GET.get('order')
    column = request.GET.get('column')
    tag_slug = request.GET.get('tag')

    # 初始化查询集
    article_list = Post.objects.all()
    filter_category = Category.objects.all()
    authorPost = article_list.order_by('-user_total_views')[:4]


    # 搜索查询集
    if search:
        article_list = article_list.filter(
            Q(title__icontains=search) |
            Q(body__icontains=search)
        )
    else:
        # 将 search 参数重置为空
        search = ''

    # 栏目查询集
    if column is not None and column.isdigit():
        article_list = article_list.filter(column=column)

    # tag
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        article_list = article_list.filter(tags__in=[tag])
        # article_list = article_list.filter(tags__name__in=[tag])

    # 查询集排序
    if order == 'total_views':
        # 按热度排序博文
        article_list = article_list.order_by('-total_views')

    # 每页显示 1 篇文章
    paginator = Paginator(article_list, 3)
    # 获取 url 中的页码
    page = request.GET.get('page')
    # 将导航对象相应的页码内容返回给 articles
    articles = paginator.get_page(page)
    # 需要传递给模板（templates）的对象
    context = {
        'articles': articles,
        'order': order,
        'search': search,
        'column': column,
        'tag': tag,
        'filter_category':filter_category,
        'trenddouble':trenddouble,
        'authorPost':authorPost
    }
    # render
    return render(request, 'account/posts.html', context)

# values_list('id', flat=True)

@login_required
def trendingpost(request,trend):
    posts = Post.objects.filter(title=trend).all()
    for post in posts:
        print(post.id)
    post.total_views  +=  1 
    post.save( update_fields = ['total_views'])
    comments = Comment.objects.filter(post=post.id)
    comment_form = CommentForm()
    total_likes = post.total_likes()
    total_dislikes = post.total_dislikes()
    liked=False
    if post.like.filter(id=request.user.id).exists():
        liked = True

    disliked = False
    if post.dislike.filter(id=request.user.id).exists():
        disliked = True
        
    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids)\
                                  .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
                                .order_by('-same_tags','-publish')[:4]

    pre_article = Post.objects.filter(id__lt=post.id).order_by('-id')
    next_article = Post.objects.filter(id__gt=post.id).order_by('id')
    if pre_article.count() > 0:
        pre_article = pre_article[0]
    else:
        pre_article = None

    if next_article.count() > 0:
        next_article = next_article[0]
    else:
        next_article = None
    
    return render(request,
                  'account/category_filter.html',
                  {'post': post,
                #    'comments': comments,
                #    'new_comment': new_comment,
                   'comment_form': comment_form,
                   'similar_posts': similar_posts,
                   'comments': comments,
                   'pre_article': pre_article,
                   'next_article': next_article, 
                   'total_likes':total_likes,
                   'liked':liked,
                   'total_dislikes':total_dislikes,
                   'disliked':disliked  
                   })

@login_required
def post_detail(request, id):
    post = get_object_or_404(Post,id=id)
    # Views+1 
    post.total_views  +=  1 
    post.save( update_fields = ['total_views'])
    # user total views
    post.user_total_views +=1
    post.save( update_fields=['user_total_views'])
    comments = Comment.objects.filter(post=id)
    comment_form = CommentForm()
    total_likes = post.total_likes()
    total_dislikes = post.total_dislikes()
    liked=False
    if post.like.filter(id=request.user.id).exists():
        liked = True

    disliked = False
    if post.dislike.filter(id=request.user.id).exists():
        disliked = True
        
    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids)\
                                  .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
                                .order_by('-same_tags','-publish')[:4]

    pre_article = Post.objects.filter(id__lt=post.id).order_by('-id')
    next_article = Post.objects.filter(id__gt=post.id).order_by('id')
    if pre_article.count() > 0:
        pre_article = pre_article[0]
    else:
        pre_article = None

    if next_article.count() > 0:
        next_article = next_article[0]
    else:
        next_article = None
    
    return render(request,
                  'account/details.html',
                  {'post': post,
                #    'comments': comments,
                #    'new_comment': new_comment,
                   'comment_form': comment_form,
                   'similar_posts': similar_posts,
                   'comments': comments,
                   'pre_article': pre_article,
                   'next_article': next_article, 
                   'total_likes':total_likes,
                   'liked':liked,
                   'total_dislikes':total_dislikes,
                   'disliked':disliked  
                   })

@login_required()
def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read {post.title}"
            message = f"Read {post.title} at {post_url}\n\n" \
                      f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'admin@myblog.com', [cd['to']])
            sent = True

    else:
        form = EmailPostForm()
    return render(request, 'account/share.html', {'post': post,
                                                    'form': form,
                                                    'sent': sent})

@login_required
def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.annotate(similarity=TrigramSimilarity('title', query),).filter(similarity__gt=0.1).order_by('-similarity')
            
    return render(request,
                  'account/search.html',
                  {'form': form,
                   'query': query,
                   'results': results})


@login_required
def post_upload(request):
    form_class = PostForm
    form = form_class(request.POST or None,request.FILES or None)
    if request.method == 'POST':
        # A comment was posted
        if form.is_valid():
            title =form.data['title']
            # avatar = form.data['avatar']
            # print(avatar)
            form.save()
            return render(request,'account/uploadsuccess.html',{'title':title})
    else:
        form = PostForm()
    return render(request,'account/uploadpost.html',{'post_form':form})

@method_decorator(login_required, name='dispatch')
class UpdatePostView(UpdateView):
    model = Post
    template_name = 'account/update_post.html'
    fields = ['title','avatar','body','status','tags']

@method_decorator(login_required, name='dispatch')
class DeletePostView(DeleteView):
    model = Post
    template_name = 'account/delete_post.html'

    def get_success_url(self):
        return reverse('posts:post_list')



class AddCategoryView(CreateView):
    model = Category
    template_name = 'account/add_category.html'
    fields = '__all__'


@login_required()
def CategoryView(request,cats):
    filter_category = Category.objects.all()
    category_post = Post.objects.filter(category=cats.replace('_',' '))
    paginator = Paginator(category_post, 3) # 3 posts in each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)
    return render (request,'account/categories.html',{'page':page,'cats':cats.title().replace('_',' '),'category_post':category_post,'posts':posts,'filter_category':filter_category})


@login_required
def PoliticsView(request):
    post_politics =Post.objects.filter(category='politics')
    return render(request, 'account/politics.html',{'post_politics':post_politics})



# follow and u follow
@login_required
def user_list(request):
    users = User.objects.filter(is_active=True)
    return render(request,
                  'account/userlist.html',
                  {'users': users})


@login_required
def user_detail(request, username):
    user_id = User.objects.filter(username= username).values_list('id',flat=True)
    for i in user_id:
        pass
    followed_people = Contact.objects.filter(user_to=i,user_from=request.user.id).values('user_to')
    stories = Post.objects.filter(author__in=followed_people) 
    count = Post.objects.filter(author=i).count()
    user = get_object_or_404(User,
                             username=username,
                             is_active=True)
    
    return render(request,
                  'account/userdetails.html',
                  {'user': user,
                    'stories':stories,
                    'total_post':count,
                    })

@ajax_required
@require_POST
@login_required
def user_follow(request):
    user_id = request.POST.get('id')
    action = request.POST.get('action')
    if user_id and action:
        try:
            user = User.objects.get(id=user_id)
            if action == 'follow':
                Contact.objects.get_or_create(user_from=request.user,
                                              user_to=user)
                create_action(request.user, 'is following', user)
            else:
                Contact.objects.filter(user_from=request.user,
                                       user_to=user).delete()
            return JsonResponse({'status':'ok'})
        except User.DoesNotExist:
            return JsonResponse({'status':'error'})
    return JsonResponse({'status':'error'})


# user activity
@login_required
def user_activity(request):
    # Display all actions by default
    actions = Action.objects.exclude(user=request.user)
          
    actions = actions.select_related('user', 'user__profile')\
                     .prefetch_related('target')[:100]
    
    
    return render(request,
                  'account/activities.html',
                  {'action': actions})


# comments 
@login_required () 
def post_comment(request, post_id, parent_comment_id=None):
    post = get_object_or_404(Post, id=post_id)

    # Process POST request
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.user = request.user

            # Secondary response
            if parent_comment_id:
                parent_comment = Comment.objects.get(id=parent_comment_id)
                # If the response level exceeds the second level, it will be converted to the second level
                new_comment.parent_id = parent_comment.get_root().id
                # Respondent
                new_comment.reply_to = parent_comment.user
                new_comment.save()
                create_action(request.user, 'comment on post', parent_comment.user)

                # Add code to send notifications to other users 
                if not parent_comment.user.is_superuser:
                    notify.send(
                        request.user,
                        recipient=parent_comment.user,
                        verb='Replied to you',
                        target=post,
                        action_object=new_comment,
                    )

                return HttpResponse("200 OK")
            new_comment.save()
            create_action(request.user, 'comment on post', new_comment.user)


             # Add code to send a notification to the administrator 
            if not request.user.is_superuser:
                notify.send(
                        request.user,
                        recipient=User.objects.filter(is_superuser=1),
                        verb='Replied to you',
                        target=post,
                        action_object=new_comment,
                    )
            return redirect(post)
        else:
            return HttpResponse("The content of the form is incorrect, please fill in again.")
    # Handling GET requests
    elif request.method == 'GET':
        comment_form = CommentForm()
        context = {
            'comment_form': comment_form,
            'post_id': post_id,
            'parent_comment_id': parent_comment_id
        }
        return render(request, 'account/reply.html', context)
    # Processing other requests
    else:
        return HttpResponse("Only GET/POST requests are accepted.")

# like 
class IncreaseLikesView(View):
    def post(self, request, *args, **kwargs):
        post = Post.objects.get(id=kwargs.get('id'))
        user =Post.objects.filter(id=kwargs.get('id')).values_list('author',flat=True)
        for i in user:
            pass
        notify.send(
                        request.user,
                        recipient=User.objects.get(id=i),
                        verb='like to your post',
                        target=post,
                        action_object=post,
                    )
        create_action(request.user, 'likes on post',User.objects.get(id=i))

        post.likes += 1
        post.save()
        return HttpResponse('success')



# history
@login_required()
def history(request):
    if request.method == "POST":
        user = request.user
        post_id = request.POST['post_id']
        history = History(user=user, post_hist_id=post_id)
        history.save()

        return redirect(f"/posts/{post_id}")

    history = History.objects.filter(user=request.user)
    ids = []
    for i in history:
        ids.append(i.post_hist_id)
    
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
    post = Post.objects.filter(id__in=ids).order_by(preserved)

    return render(request, 'account/history.html', {"history": post})

@login_required()
def watchlater(request):
    if request.method == "POST":
        user = request.user
        post_watch_id = request.POST['post_id']
        watch = Watchlater.objects.filter(user=user)
        
        for i in watch:
            if post_watch_id == i.post_watch_id:
                message = "Your Post is Already Added"
                break
        else:
            watchlater = Watchlater(user=user, post_watch_id=post_watch_id)
            watchlater.save()
            message = "Your post is Succesfully Added"

    wl = Watchlater.objects.filter(user=request.user)
    ids = []
    for i in wl:
        ids.append(i.post_watch_id)
    
    preserved1 = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
    post = Post.objects.filter(id__in=ids).order_by(preserved1)

    return render(request, "account/watchlater.html", {'post': post})

# delete history
@login_required()
def DeleteHistory(request,id):
    history = History.objects.filter(user_id=id).delete()
    return redirect('/posts/history')


# delete history particular post
@login_required()
def DeletePerHistory(request,id,user):
    history = History.objects.filter(post_hist_id=id,user_id=user).delete()
    return redirect('/posts/history')

# delete watchlater
@login_required()
def DeleteWatchLater(request,id):
    watchlater = Watchlater.objects.filter(user_id=id).delete()
    return redirect('/posts/watchlater')

# delete per post watch later
@login_required()
def DeletePerWatchLater(request,id,user):
    watchlater = Watchlater.objects.filter(post_watch_id=id,user_id=user).delete()
    return redirect('/posts/watchlater')

# block unblock user 
def BlockedUser(request):
    username =1
    blocked_users = User.objects.filter(blocked_by__blocked_user=username)
    post = Post.objects.filter(~Q(author__in=blocked_users))
    print(blocked_users)
    print(post)
    return HttpResponse('done')
# publish__gte=long_ago
@login_required()
def TimeLine(request):
    followed_people = Contact.objects.filter(user_from=request.user.id).values_list('user_to',flat=True)
    stories = Post.objects.filter(author__in=followed_people,publish__gte=long_ago_timeline)
    paginator = Paginator(stories,4)
    page = request.GET.get('page')
    stories = paginator.get_page(page)
    return render(request,
                  'account/timeline.html',
                  {'stories': stories})

@login_required()
def pie_chart(request):
    labels = []
    data = []
    likes = []
    dislike = []
    views = []

    queryset = Post.objects.order_by('-total_views')
    for like in queryset:
        labels.append(like.title)
        views.append(like.total_views)
        likes.append(like.total_likes())
        dislike.append(like.total_dislikes())

    return render(request, 'account/charts.html', {'views':views,'likes':likes,'labels':labels,'dislike':dislike})    

   


@login_required()
def LikeView(request ,pk):
    post =get_object_or_404(Post, id=request.POST.get('post_id'))
    liked=False
    if post.like.filter(id=request.user.id).exists():
        post.like.remove(request.user)
        liked=False
    else:
        post.like.add(request.user)
        if post.dislike.filter(id=request.user.id).exists():
            post.dislike.remove(request.user)
        liked=True
    return HttpResponseRedirect(reverse('posts:post_detail',args=[str(pk)]))


@login_required()
def DisLikeView(request ,pk):
    post =get_object_or_404(Post, id=request.POST.get('post_id'))
    disliked=False
    if post.dislike.filter(id=request.user.id).exists():
        post.dislike.remove(request.user)
        disliked=False
    else:
        post.dislike.add(request.user)
        if post.like.filter(id=request.user.id).exists():
            post.like.remove(request.user)
        disliked=True
    return HttpResponseRedirect(reverse('posts:post_detail',args=[str(pk)]))

def handler404(request, exception):
    response = render(request, "account/handlers/404.html", {})
    response.status_code = 404
    return response
def handler500(request):
    return render(request, 'account/handlers/500.html', status=500)




