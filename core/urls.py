"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from core.base.views import ImportTransactionsView, recategorize_transactions


class URLConstant:
    ADMIN = "admin/"
    IMPORT_TRANSACTIONS = "import-transactions/"
    RECATEGORIZE_TRANSACTIONS = "recategorize-transactions/"


urlpatterns = [
    path(URLConstant.ADMIN, admin.site.urls),
    path(
        URLConstant.IMPORT_TRANSACTIONS,
        ImportTransactionsView.as_view(),
        name="import-transactions",
    ),
    path(
        URLConstant.RECATEGORIZE_TRANSACTIONS,
        recategorize_transactions,
        name="recategorize-transactions",
    ),
]
