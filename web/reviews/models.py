from django.contrib.auth.models import User
from django.db import models

# Create your models here.
PUB_STATUS_CHOICES = (
    ('DR', 'Черновик'),
    ('PB', 'Опубликовано'),
)

"""
...................................................
...................... Status model ...............
...................................................
"""


class Status(models.Model):
    class Meta:
        verbose_name = 'Статус'
        verbose_name_plural = 'Статусы'

    slug = models.CharField(primary_key=True, max_length=2, unique=True,
                            help_text="Значение статуса, хранящееся в БД"
                                      "(например для title='отклонено' возможные slug='RJ')")
    title = models.CharField(max_length=64, unique=True, null=True,
                             help_text="Наименование статуса (желательно в 3-м лице)")

    def __str__(self):
        return self.title

    @classmethod
    def get_choices(cls):
        return tuple((x.slug, x.title) for x in cls.objects.all())


"""
...................................................
........................ Review model .............
...................................................
"""


class Review(models.Model):
    # TODO: protect
    # TODO: status choices in admin
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    TYPES_CHOICES = (
        ("ID", "Идея"),
        ("TH", "Благодарность"),
        ("PR", "Проблема"),
        ("QU", "Вопрос"),
    )

    type = models.CharField(max_length=2, choices=TYPES_CHOICES, default="ID", help_text="Тип отзыва")
    status = models.ForeignKey(Status, help_text="Состояние обработки отзыва", on_delete=models.CASCADE,
                               default="WA")
    title = models.CharField(max_length=128, help_text="Заголовок отзыва")
    content = models.TextField(help_text="Содержание отзыва")
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, blank=True, help_text="Автор отзыва", on_delete=models.CASCADE)
    likes = models.ManyToManyField(User, related_name="likes", blank=True,
                                   help_text="Пользователи, которым понравился отзыв")
    dislikes = models.ManyToManyField(User, related_name="dislikes", blank=True,
                                      help_text="Пользователи, которым не понравился отзыв")
    pub_state = models.CharField(max_length=2, choices=PUB_STATUS_CHOICES, default="DR",
                                 help_text="Состояние публикации отзыва")

    def __str__(self):
        return "#{id}: {title}".format(id=self.id, title=self.title[:16])

    def is_liked(self, user: User):
        return self.likes.filter(id=user.id).exists()

    def is_disliked(self, user: User):
        return self.dislikes.filter(id=user.id).exists()

    def is_my(self, user: User):
        return self.author == user

    def is_published(self):
        return self.pub_state == "PB"

    @property
    def get_count_of_published_comments(self):
        return self.comments.filter(pub_state="PB").count()


"""
...................................................
........................ Comment model  ...........
...................................................
"""


class Comment(models.Model):
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               help_text="Автор комментария")  # TODO: protect, auto
    content = models.TextField(help_text="Содержание комментария")
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="comments",
                               help_text="Отзыв, к которому был оставлен комментарий")
    date = models.DateTimeField(auto_now_add=True)
    pub_state = models.CharField(max_length=2, choices=PUB_STATUS_CHOICES, default="DR",
                                 help_text="Состояние публикации комментария")

    @property
    def short_content(self):
        return self.content[:64] + "..."

    def is_published(self):
        return self.pub_state == "PB"
