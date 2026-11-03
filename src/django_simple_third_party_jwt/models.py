from django.contrib.auth.models import User
from django.db import models


class SocialAccount(models.Model):
    """
    第三方帳號模型
    記錄哪個 Google 或 Microsoft 帳號對應到哪個 Django 使用者。
    一個使用者可以有多筆（`user.social.all()`）。
    """

    # 第三方登入的提供者："google" 或 "microsoft"
    provider = models.CharField(
        max_length=200,
        default="",  # 預設值為空字串
        verbose_name="提供者",
        blank=True,
    )

    # 第三方平台上的帳號識別碼：
    # - Google：ID token 裡的 `sub`（每個 Google 帳號固定不變的 ID）
    # - Microsoft：ID token 裡的 `preferred_username`（看起來像 email 的帳號名稱）
    unique_id = models.CharField(
        verbose_name="唯一ID",
        max_length=200,
    )

    # 關聯到 Django 內建的 User 模型（一對多）
    user = models.ForeignKey(
        User,
        verbose_name="使用者",
        related_name="social",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "social_account"
        verbose_name_plural = "第三方登入（3rd party login）"
        verbose_name = "第三方登入（3rd party login）"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.provider}"
