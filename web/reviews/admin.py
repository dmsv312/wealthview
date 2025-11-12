from django.contrib import admin
from .models import *


# Register your models here.
class StatusAdmin(admin.ModelAdmin):
    list_display = ('slug', 'title')


class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'short_content', 'date', 'author', 'pub_state')


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'status', 'title', 'date', 'author', 'pub_state')
    readonly_fields = ('likes', 'dislikes')


admin.site.register(Status, StatusAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Review, ReviewAdmin)
