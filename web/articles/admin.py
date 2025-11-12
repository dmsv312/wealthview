from django.contrib import admin
from .models import *


# Register your models here.
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'date', 'category', )
    search_fields = ('title', 'content')
    readonly_fields = ('slug', )
    prepopulated_fields = {'seo_title': ('title', )}


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent')
    readonly_fields = ('slug',)


admin.site.register(Article, ArticleAdmin)
admin.site.register(Category, CategoryAdmin)
