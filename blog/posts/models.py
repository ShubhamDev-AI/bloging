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
from django.db.models import Q
from django.dispatch import Signal
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


friendship_request_created = Signal()
friendship_request_rejected = Signal()
friendship_request_canceled = Signal()
friendship_request_viewed = Signal()
friendship_request_accepted = Signal(providing_args=["from_user", "to_user"])
friendship_removed = Signal(providing_args=["from_user", "to_user"])
follower_created = Signal(providing_args=["follower"])
follower_removed = Signal(providing_args=["follower"])
followee_created = Signal(providing_args=["followee"])
followee_removed = Signal(providing_args=["followee"])
following_created = Signal(providing_args=["following"])
following_removed = Signal(providing_args=["following"])
block_created = Signal(providing_args=["blocker"])
block_removed = Signal(providing_args=["blocker"])

CACHE_TYPES = {
    "friends": "f-%s",
    "followers": "fo-%s",
    "following": "fl-%s",
    "blocks": "b-%s",
    "blocked": "bo-%s",
    "blocking": "bd-%s",
    "requests": "fr-%s",
    "sent_requests": "sfr-%s",
    "unread_requests": "fru-%s",
    "unread_request_count": "fruc-%s",
    "read_requests": "frr-%s",
    "rejected_requests": "frj-%s",
    "unrejected_requests": "frur-%s",
    "unrejected_request_count": "frurc-%s",
}

BUST_CACHES = {
    "friends": ["friends"],
    "followers": ["followers"],
    "blocks": ["blocks"],
    "blocked": ["blocked"],
    "following": ["following"],
    "blocking": ["blocking"],
    "requests": [
        "requests",
        "unread_requests",
        "unread_request_count",
        "read_requests",
        "rejected_requests",
        "unrejected_requests",
        "unrejected_request_count",
    ],
    "sent_requests": ["sent_requests"],
}

def cache_key(type, user_pk):
    """
    Build the cache key for a particular type of cached value
    """
    return CACHE_TYPES[type] % user_pk

def bust_cache(type, user_pk):
    """
    Bust our cache for a given type, can bust multiple caches
    """
    bust_keys = BUST_CACHES[type]
    keys = [CACHE_TYPES[k] % user_pk for k in bust_keys]
    cache.delete_many(keys)

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

class ContentTypeModel(object):
    
    def get_content_type(self):
        """ function to get the content_type object for current model """
        return ContentType.objects.get_for_model(self)

# post models
class Post(models.Model,ContentTypeModel):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250,unique_for_date='publish')
    author = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              related_name='blog_posts')
    avatar = models.FileField(default='avatar.png',upload_to='media/%Y%m%d/', blank=True)
    body = RichTextField(blank=True ,null=True)
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10,
                              choices=STATUS_CHOICES,
                              default='draft')
    likes = models.PositiveIntegerField(default=0)
    like = models.ManyToManyField(User,blank=True)
    dislike = models.ManyToManyField(User,related_name='blog_post_dislike')    
    total_views =models.PositiveIntegerField(default=0)
    user_total_views =models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=210,default='web technology')
    objects = models.Manager() # The default manager.
    published = PublishedManager() # Our custom manager.
    tags = TaggableManager()
    deleted_at = models.DateTimeField(null=True, blank=True)


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
    
    # @property
    # def total_visitors(self):
    #     return Visitor.objects.filter(post__pk=self.pk).count()
    def get_content_type(self):
        """ function to get the content_type object for this model """
        self.content_type = super().get_content_type()
        return self.content_type

    def get_visitors(self):
        """ function to get the queryset of visitors """
        if hasattr(self, 'content_type'):
            content_type = self.content_type
        else:
            content_type = self.get_content_type()
        queries = {'content_type': content_type, 'object_id': self.id}
        return Visitor.objects.published().filter(**queries)

    @property
    def total_visitors(self):
        """ count the total of visitors """
        return self.get_visitors().count()

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
    
    def get_absolute_url(self):
        return reverse('posts:post_list')


# watch later and history
class Watchlater(models.Model):
    watch_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post_watch_id = models.CharField(max_length=10000000, default="")

class History(models.Model):
    hist_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post_hist_id = models.CharField(max_length=10000000, default="")

class FriendshipRequest(models.Model):
    """ Model to represent friendship requests """

    from_user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name="friendship_requests_sent",
    )
    to_user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name="friendship_requests_received",
    )

    message = models.TextField(_("Message"), blank=True)

    created = models.DateTimeField(default=timezone.now)
    rejected = models.DateTimeField(blank=True, null=True)
    viewed = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _("Friendship Request")
        verbose_name_plural = _("Friendship Requests")
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return "%s" % self.from_user_id

    def accept(self):
        """ Accept this friendship request """
        Friend.objects.create(from_user=self.from_user, to_user=self.to_user)

        Friend.objects.create(from_user=self.to_user, to_user=self.from_user)

        friendship_request_accepted.send(
            sender=self, from_user=self.from_user, to_user=self.to_user
        )

        self.delete()

        # Delete any reverse requests
        FriendshipRequest.objects.filter(
            from_user=self.to_user, to_user=self.from_user
        ).delete()

        # Bust requests cache - request is deleted
        bust_cache("requests", self.to_user.pk)
        bust_cache("sent_requests", self.from_user.pk)
        # Bust reverse requests cache - reverse request might be deleted
        bust_cache("requests", self.from_user.pk)
        bust_cache("sent_requests", self.to_user.pk)
        # Bust friends cache - new friends added
        bust_cache("friends", self.to_user.pk)
        bust_cache("friends", self.from_user.pk)

        return True

    def reject(self):
        """ reject this friendship request """
        self.rejected = timezone.now()
        self.save()
        friendship_request_rejected.send(sender=self)
        bust_cache("requests", self.to_user.pk)

    def cancel(self):
        """ cancel this friendship request """
        self.delete()
        friendship_request_canceled.send(sender=self)
        bust_cache("requests", self.to_user.pk)
        bust_cache("sent_requests", self.from_user.pk)
        return True

    def mark_viewed(self):
        self.viewed = timezone.now()
        friendship_request_viewed.send(sender=self)
        self.save()
        bust_cache("requests", self.to_user.pk)
        return True

class FriendshipManager(models.Manager):
    """ Friendship manager """

    def friends(self, user):
        """ Return a list of all friends """
        key = cache_key("friends", user.pk)
        friends = cache.get(key)

        if friends is None:
            qs = (
                Friend.objects.select_related("from_user", "to_user")
                .filter(to_user=user)
                .all()
            )
            friends = [u.from_user for u in qs]
            cache.set(key, friends)

        return friends

    def requests(self, user):
        """ Return a list of friendship requests """
        key = cache_key("requests", user.pk)
        requests = cache.get(key)

        if requests is None:
            qs = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user)
                .all()
            )
            requests = list(qs)
            cache.set(key, requests)

        return requests

    def sent_requests(self, user):
        """ Return a list of friendship requests from user """
        key = cache_key("sent_requests", user.pk)
        requests = cache.get(key)

        if requests is None:
            qs = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(from_user=user)
                .all()
            )
            requests = list(qs)
            cache.set(key, requests)

        return requests

    def unread_requests(self, user):
        """ Return a list of unread friendship requests """
        key = cache_key("unread_requests", user.pk)
        unread_requests = cache.get(key)

        if unread_requests is None:
            qs = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user, viewed__isnull=True)
                .all()
            )
            unread_requests = list(qs)
            cache.set(key, unread_requests)

        return unread_requests

    def unread_request_count(self, user):
        """ Return a count of unread friendship requests """
        key = cache_key("unread_request_count", user.pk)
        count = cache.get(key)

        if count is None:
            count = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user, viewed__isnull=True)
                .count()
            )
            cache.set(key, count)

        return count

    def read_requests(self, user):
        """ Return a list of read friendship requests """
        key = cache_key("read_requests", user.pk)
        read_requests = cache.get(key)

        if read_requests is None:
            qs = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user, viewed__isnull=False)
                .all()
            )
            read_requests = list(qs)
            cache.set(key, read_requests)

        return read_requests

    def rejected_requests(self, user):
        """ Return a list of rejected friendship requests """
        key = cache_key("rejected_requests", user.pk)
        rejected_requests = cache.get(key)

        if rejected_requests is None:
            qs = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user, rejected__isnull=False)
                .all()
            )
            rejected_requests = list(qs)
            cache.set(key, rejected_requests)

        return rejected_requests

    def unrejected_requests(self, user):
        """ All requests that haven't been rejected """
        key = cache_key("unrejected_requests", user.pk)
        unrejected_requests = cache.get(key)

        if unrejected_requests is None:
            qs = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user, rejected__isnull=True)
                .all()
            )
            unrejected_requests = list(qs)
            cache.set(key, unrejected_requests)

        return unrejected_requests

    def unrejected_request_count(self, user):
        """ Return a count of unrejected friendship requests """
        key = cache_key("unrejected_request_count", user.pk)
        count = cache.get(key)

        if count is None:
            count = (
                FriendshipRequest.objects.select_related("from_user", "to_user")
                .filter(to_user=user, rejected__isnull=True)
                .count()
            )
            cache.set(key, count)

        return count

    def add_friend(self, from_user, to_user, message=None):
        """ Create a friendship request """
        if from_user == to_user:
            raise ValidationError("Users cannot be friends with themselves")

        if self.are_friends(from_user, to_user):
            raise AlreadyFriendsError("Users are already friends")

        if self.can_request_send(from_user, to_user):
            raise AlreadyExistsError("Friendship already requested")

        if message is None:
            message = ""

        request, created = FriendshipRequest.objects.get_or_create(
            from_user=from_user, to_user=to_user
        )

        if created is False:
            raise AlreadyExistsError("Friendship already requested")

        if message:
            request.message = message
            request.save()

        bust_cache("requests", to_user.pk)
        bust_cache("sent_requests", from_user.pk)
        friendship_request_created.send(sender=request)

        return request

    def can_request_send(self, from_user, to_user):
        """ Checks if a request was sent """
        if from_user == to_user:
            return False

        if not FriendshipRequest.objects.filter(
            from_user=from_user, to_user=to_user
        ).exists():
            return False

        return True

    def remove_friend(self, from_user, to_user):
        """ Destroy a friendship relationship """
        try:
            qs = (
                Friend.objects.filter(
                    Q(to_user=to_user, from_user=from_user)
                    | Q(to_user=from_user, from_user=to_user)
                )
                .distinct()
                .all()
            )

            if qs:
                friendship_removed.send(
                    sender=qs[0], from_user=from_user, to_user=to_user
                )
                qs.delete()
                bust_cache("friends", to_user.pk)
                bust_cache("friends", from_user.pk)
                return True
            else:
                return False
        except Friend.DoesNotExist:
            return False

    def are_friends(self, user1, user2):
        """ Are these two users friends? """
        friends1 = cache.get(cache_key("friends", user1.pk))
        friends2 = cache.get(cache_key("friends", user2.pk))
        if friends1 and user2 in friends1:
            return True
        elif friends2 and user1 in friends2:
            return True
        else:
            try:
                Friend.objects.get(to_user=user1, from_user=user2)
                return True
            except Friend.DoesNotExist:
                return False

class Friend(models.Model):
    """ Model to represent Friendships """

    to_user = models.ForeignKey('auth.User', models.CASCADE, related_name="friends")
    from_user = models.ForeignKey(
        'auth.User', models.CASCADE, related_name="_unused_friend_relation"
    )
    created = models.DateTimeField(default=timezone.now)

    objects = FriendshipManager()

    class Meta:
        verbose_name = _("Friend")
        verbose_name_plural = _("Friends")
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return "User #%s is friends with #%s" % (self.to_user_id, self.from_user_id)

    def save(self, *args, **kwargs):
        # Ensure users can't be friends with themselves
        if self.to_user == self.from_user:
            raise ValidationError("Users cannot be friends with themselves.")
        super(Friend, self).save(*args, **kwargs)

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
class Follow(models.Model):
    follower = models.ForeignKey('auth.User',
                                  related_name='followings',
                                  on_delete=models.CASCADE)
    followee = models.ForeignKey('auth.User',
                                related_name='follower',
                                on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True,
                                   db_index=True)
    objects = FollowingManager()

    class Meta:
        verbose_name = _("Following")
        verbose_name_plural = _("Following")
        unique_together = ('follower', 'followee')
        ordering = ('-created',)

    def __str__(self):
        return "User #%s follows #%s" % (self.follower, self.followee)
        # return f'{self.user_from} follows {self.user_to}'

    def save(self, *args, **kwargs):
        # Ensure users can't be friends with themselves
        if self.follower == self.followee:
            raise ValidationError("Users cannot follow themselves.")
        super(Follow, self).save(*args, **kwargs)

# Add following field to User dynamically
user_model = get_user_model()
user_model.add_to_class('following',
                        models.ManyToManyField('self',
                                                through=Follow,
                                                related_name='followers',
                                                symmetrical=False))


class BlockManager(models.Manager):
    """ Following manager """

    def blocked(self, user):
        """ Return a list of all blocks """
        key = cache_key("blocked", user.pk)
        blocked = cache.get(key)

        if blocked is None:
            qs = Block.objects.filter(blocked=user).all()
            blocked = [u.blocked for u in qs]
            cache.set(key, blocked)

        return blocked

    def blocking(self, user):
        """ Return a list of all users the given user blocks """
        key = cache_key("blocking", user.pk)
        blocking = cache.get(key)

        if blocking is None:
            qs = Block.objects.filter(blocker=user).all()
            blocking = [u.blocked for u in qs]
            cache.set(key, blocking)

        return blocking

    def add_block(self, blocker, blocked):
        """ Create 'follower' follows 'followee' relationship """
        if blocker == blocked:
            raise ValidationError("Users cannot block themselves")

        relation, created = Block.objects.get_or_create(
            blocker=blocker, blocked=blocked
        )

        if created is False:
            raise AlreadyExistsError(
                "User '%s' already blocks '%s'" % (blocker, blocked)
            )

        block_created.send(sender=self, blocker=blocker)
        block_created.send(sender=self, blocked=blocked)
        block_created.send(sender=self, blocking=relation)

        bust_cache("blocked", blocked.pk)
        bust_cache("blocking", blocker.pk)

        return relation

    def remove_block(self, blocker, blocked):
        """ Remove 'blocker' blocks 'blocked' relationship """
        try:
            rel = Block.objects.get(blocker=blocker, blocked=blocked)
            block_removed.send(sender=rel, blocker=rel.blocker)
            block_removed.send(sender=rel, blocked=rel.blocked)
            block_removed.send(sender=rel, blocking=rel)
            rel.delete()
            bust_cache("blocked", blocked.pk)
            bust_cache("blocking", blocker.pk)
            return True
        except Follow.DoesNotExist:
            return False

    def is_blocked(self, user1, user2):
        """ Are these two users blocked? """
        block1 = cache.get(cache_key("blocks", user1.pk))
        block2 = cache.get(cache_key("blocks", user2.pk))
        if block1 and user2 in block1:
            return True
        elif block2 and user1 in block2:
            return True
        else:
            try:
                Block.objects.get(blocker=user1, blocked=user2)
                return True
            except Block.DoesNotExist:
                return False

class Block(models.Model):
    """ Model to represent Following relationships """

    blocker = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name="blocking"
    )
    blocked = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name="blockees"
    )
    created = models.DateTimeField(default=timezone.now)

    objects = BlockManager()

    class Meta:
        verbose_name = _("Blocked Relationship")
        verbose_name_plural = _("Blocked Relationships")
        unique_together = ("blocker", "blocked")

    def __str__(self):
        return "User #%s blocks #%s" % (self.blocker_id, self.blocked_id)

    def save(self, *args, **kwargs):
        # Ensure users can't be friends with themselves
        if self.blocker == self.blocked:
            raise ValidationError("Users cannot block themselves.")
        super(Block, self).save(*args, **kwargs)

class DefaultManager(models.Manager):
    
    def published(self):
        """ return queryset for not-deleted objects only. """
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """ return queryset for deleted objects only. """
        return self.filter(deleted_at__isnull=False)

    def get_or_none(self, **kwargs):
        """ function to get the object or None. """
        try:
            return self.get(**kwargs)
        except (Exception, self.model.DoesNotExist):
            return None

class Visitor(models.Model):
    id = models.BigAutoField(primary_key=True)
    headers = models.TextField(_('Headers'), null=True, blank=True)
    ip_address = models.CharField(_('IP Address'), max_length=40)
    object_id = models.BigIntegerField()
    content_type = models.ForeignKey(ContentType, related_name='visitors',
                                     on_delete=models.CASCADE)
    content_object = GenericForeignKey('content_type', 'object_id')
    deleted_at = models.DateTimeField(null=True, blank=True)


    objects = DefaultManager()

    def __str__(self):
        message = _('%(ip_address)s visited to %(content_object)s')
        return message % {'ip_address': self.ip_address,
                          'content_object': self.content_object}

    class Meta:
        verbose_name = _('Visitor')
        verbose_name_plural = _('Visitors')
        unique_together = ('ip_address', 'object_id', 'content_type')
        # ordering = ['-created']


        


