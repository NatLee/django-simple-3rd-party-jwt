from django.contrib import admin
from django.contrib.auth import get_user_model

from django_simple_third_party_jwt.models import SocialAccount
from django_simple_third_party_jwt.utils.accounts import has_field

_user_model = get_user_model()
# The user model's own login-name and e-mail fields (AUTH_USER_MODEL may call them anything).
_user_search_fields = [
    f"user__{name}"
    for name in dict.fromkeys([_user_model.USERNAME_FIELD, _user_model.get_email_field_name()])
    if has_field(_user_model, name)
]


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    """SocialAccount 模型的管理 UI 配置"""

    list_display = ("user", "user_email", "provider", "unique_id")
    # 在列表頁中可以直接編輯的字段
    list_editable = ("provider",)
    list_filter = ("provider",)
    list_per_page = 25
    search_fields = _user_search_fields + ["provider", "unique_id"]

    def get_readonly_fields(self, request, obj=None):
        # 新增時可以填 unique_id，管理員才能把社群登入手動連到既有使用者（README 有步驟）；
        # 存好之後就不能改。
        return () if obj is None else ("unique_id",)

    @admin.display(description="使用者Email")
    def user_email(self, obj: SocialAccount) -> str:
        """顯示使用者的 Email"""
        return getattr(obj.user, obj.user.get_email_field_name(), "")
