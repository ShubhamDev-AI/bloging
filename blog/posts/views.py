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
import redis
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

def search(request):
    user_list = User.objects.all()
    user_filter = UserFilter(request.GET, queryset=user_list)
    return render(request, 'account/user_filter.html', {'filter': user_filter})


from django.contrib.auth.models import User

# @login_required
def post_list(request):
    search = request.GET.get('search')
    order = request.GET.get('order')
    column = request.GET.get('column')
    tag = request.GET.get('tag')

    # 初始化查询集
    article_list = Post.objects.all()

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

    # 标签查询集
    if tag and tag != 'None':
        article_list = article_list.filter(tags__name__in=[tag])

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
    }
    # render
    return render(request, 'account/posts.html', context)

    

@login_required
def post_detail(request, id):
    post = get_object_or_404(Post,id=id)
    print(post.id)
    # Views+1 
    post.total_views  +=  1 
    post.save( update_fields = ['total_views'])
    comments = Comment.objects.filter(post=id)
    comment_form = CommentForm()


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
                #    'comment_form': comment_form,
                   'similar_posts': similar_posts,
                   'comments': comments,
                    
                    
                   
                   })


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
    form = form_class(request.POST or None)

    if request.method == 'POST':
        # A comment was posted
        if form.is_valid():
            # Save the comment to the database
            # print (form['title'].value())
            # print (form.data['title'])
            title =form.data['title']
            form.save()
            # print(form.title)
            return render(request,
                          'account/uploadsuccess.html',{'title':title}
                          )
    else:
        form = PostForm()

    return render(request,
                  'account/uploadpost.html',
                  {'post_form':form
                    })

@method_decorator(login_required, name='dispatch')
class UpdatePostView(UpdateView):
    model = Post
    template_name = 'account/update_post.html'
    fields = ['title','slug','body','status','tags']

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



def CategoryView(request,cats):
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
    return render (request,'account/categories.html',{'page':page,'cats':cats.title().replace('_',' '),'category_post':category_post,'posts':posts})


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
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    print(ip)
    user_id = User.objects.filter(username= username).values_list('id',flat=True)
    for i in user_id:
        pass
    followed_people = Contact.objects.filter(user_from=i).values('user_to')
    stories = Post.objects.filter(author__in=followed_people) 

    user = get_object_or_404(User,
                             username=username,
                             is_active=True)
    
    return render(request,
                  'account/userdetails.html',
                  {'user': user,
                    'stories':stories
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
    following_ids = request.user.following.values_list('id',
                                                       flat=True)
    if following_ids:
        # If user is following others, retrieve only their actions
        actions = actions.filter(user_id__in=following_ids)
    actions = actions.select_related('user', 'user__profile')\
                     .prefetch_related('target')[:10]

    return render(request,
                  'account/activities.html',
                  {'actions': actions})


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
                return HttpResponse('200 OK')

            new_comment.save()
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
        post.likes += 1
        post.save()
        return HttpResponse('success')

