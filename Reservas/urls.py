from django.contrib import admin
from django.urls import (
    include,
    path,
)


urlpatterns = [

    # =====================================================
    # ADMIN DE DJANGO
    # =====================================================

    path(
        "admin/",
        admin.site.urls,
    ),


    # =====================================================
    # URLS DE LA APLICACIÓN
    # =====================================================

    path(
        "",
        include(
            "webapp.urls"
        ),
    ),
]