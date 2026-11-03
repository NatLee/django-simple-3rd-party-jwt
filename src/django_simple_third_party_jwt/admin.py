from django.contrib import admin

from django_simple_third_party_jwt.models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    """SocialAccount 模型的管理 UI 配置"""

    list_display = ("user", "user_email", "provider", "unique_id")
    # 在列表頁中可以直接編輯的字段
    list_editable = ("provider",)
    list_filter = ("provider",)
    list_per_page = 25
    search_fields = ["user__username", "user__email", "provider", "unique_id"]
    # 只讀字段（在編輯頁面中不可修改）
    readonly_fields = ("unique_id",)

    @admin.display(description="使用者Email")
    def user_email(self, obj: SocialAccount) -> str:
        """顯示使用者的 Email"""
        return obj.user.email
