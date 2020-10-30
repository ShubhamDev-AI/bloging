from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
from taggit.managers import TaggableManager
from django.conf import settings
from django.contrib.auth import get_user_model
# django-ckeditor
from ckeditor.fields import RichTextField
# django-mptt
from mptt.models import MPTTModel, TreeForeignKey
from PIL import Image
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.cache import cache
from posts.exceptions import AlreadyExistsError, AlreadyFriendsError




class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='published')

# category models
class Category(models.Model):
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('posts:post_list')


# post models
class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250,unique_for_date='publish')
    author = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              related_name='blog_posts')
    avatar = models.FileField(upload_to='media/%Y%m%d/', blank=True)
    body = RichTextField(blank=True ,null=True)
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10,
                              choices=STATUS_CHOICES,
                              default='draft')
    likes = models.PositiveIntegerField(default=0)
    like = models.ManyToManyField(User,related_name='blog_post')
    dislike = models.ManyToManyField(User,related_name='blog_post_dislike')    
    total_views =models.PositiveIntegerField(default=0)
    user_total_views =models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=210,default='web technology')
    objects = models.Manager() # The default manager.
    published = PublishedManager() # Our custom manager.
    tags = TaggableManager()

    class Meta:
        ordering = ('-publish',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('posts:post_detail', args=[self.id])

    def save(self, *args, **kwargs):
        # Call the original save() function
        post = super(Post, self).save(*args, **kwargs)

        # Fixed width zoom image size
        if self.avatar and not kwargs.get('update_fields'):
            image = Image.open(self.avatar)
            (x, y) = image.size
            new_x = 400
            new_y = int(new_x * (y / x))
            resized_image = image.resize((new_x, new_y), Image.ANTIALIAS)
            resized_image.save(self.avatar.path)

        return post

    def was_created_recently(self):
        # If the article is published within 1 minute, return True
        diff = timezone.now() - self.created
        
        # if diff.days <= 0 and diff.seconds < 60:
        if diff.days == 0 and diff.seconds >= 0 and diff.seconds < 60:
            return True
        else:
            return False

    def total_likes(self):
        return self.like.count()

    def total_dislikes(self):
        return self.dislike.count()




# comments
class Comment(MPTTModel):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )

    # mptt树形结构
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    # 记录二级评论回复给谁, str
    reply_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replyers'
    )

    body = RichTextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ['created']

    def __str__(self):
        return self.body[:20]

# watch later and history
class Watchlater(models.Model):
    watch_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post_watch_id = models.CharField(max_length=10000000, default="")

class History(models.Model):
    hist_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post_hist_id = models.CharField(max_length=10000000, default="")


class FollowingManager(models.Manager):
    """ Following manager """

    def followers(self, user):
        """ Return a list of all followers """
        key = cache_key("followers", user.pk)
        followers = cache.get(key)

        if followers is None:
            qs = Follow.objects.filter(followee=user).all()
            followers = [u.follower for u in qs]
            cache.set(key, followers)

        return followers

    def following(self, user):
        """ Return a list of all users the given user follows """
        key = cache_key("following", user.pk)
        following = cache.get(key)

        if following is None:
            qs = Follow.objects.filter(follower=user).all()
            following = [u.followee for u in qs]
            cache.set(key, following)

        return following

    def add_follower(self, follower, followee):
        """ Create 'follower' follows 'followee' relationship """
        if follower == followee:
            raise ValidationError("Users cannot follow themselves")

        relation, created = Follow.objects.get_or_create(
            follower=follower, followee=followee
        )

        if created is False:
            raise AlreadyExistsError(
                "User '%s' already follows '%s'" % (follower, followee)
            )

        follower_created.send(sender=self, follower=follower)
        followee_created.send(sender=self, followee=followee)
        following_created.send(sender=self, following=relation)

        bust_cache("followers", followee.pk)
        bust_cache("following", follower.pk)

        return relation

    def remove_follower(self, follower, followee):
        """ Remove 'follower' follows 'followee' relationship """
        try:
            rel = Follow.objects.get(follower=follower, followee=followee)
            follower_removed.send(sender=rel, follower=rel.follower)
            followee_removed.send(sender=rel, followee=rel.followee)
            following_removed.send(sender=rel, following=rel)
            rel.delete()
            bust_cache("followers", followee.pk)
            bust_cache("following", follower.pk)
            return True
        except Follow.DoesNotExist:
            return False

    def follows(self, follower, followee):
        """ Does follower follow followee? Smartly uses caches if exists """
        followers = cache.get(cache_key("following", follower.pk))
        following = cache.get(cache_key("followers", followee.pk))

        if followers and followee in followers:
            return True
        elif following and follower in following:
            return True
        else:
            return Follow.objects.filter(follower=follower, followee=followee).exists()

# follow and unfollow system
class Contact(models.Model):
    user_from = models.ForeignKey('auth.User',
                                  related_name='rel_from_set',
                                  on_delete=models.CASCADE)
    user_to = models.ForeignKey('auth.User',
                                related_name='rel_to_set',
                                on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True,
                                   db_index=True)
    objects = FollowingManager()

    class Meta:
        verbose_name = _("Following Relationship")
        verbose_name_plural = _("Following Relationships")
        unique_together = ('user_from', 'user_to')
        ordering = ('-created',)

    def __str__(self):
        return "User #%s follows #%s" % (self.user_from, self.user_to)
        # return f'{self.user_from} follows {self.user_to}'

    def save(self, *args, **kwargs):
        # Ensure users can't be friends with themselves
        if self.user_from == self.user_to:
            raise ValidationError("Users cannot follow themselves.")
        super(Contact, self).save(*args, **kwargs)

# Add following field to User dynamically
user_model = get_user_model()
user_model.add_to_class('following',
                        models.ManyToManyField('self',
                                                through=Contact,
                                                related_name='followers',
                                                symmetrical=False))

