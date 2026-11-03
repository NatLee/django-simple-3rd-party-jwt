
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Included at the root, as in the README: JWT_3RD_PREFIX supplies the "api/" part.
    path('', include('django_simple_third_party_jwt.urls')),
]
