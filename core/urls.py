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

from constants import URLConstants
from core.base.views import (
    ImportTransactionsView,
    RecategorizeTransactionsView,
    CreateKeywordView,
    DeleteKeywordsView,
    CreateCategoryView,
    DeleteCategoriesView,
    CreateSubcategoryView,
    DeleteSubcategoriesView,
    CreateBankAccountView,
    DeleteBankAccountsView,
    CreateCSVMappingView,
    DeleteCSVMappingsView,
    CreateTagView,
    DeleteTagsView,
)

urlpatterns = [
    path(URLConstants.ADMIN, admin.site.urls),
    path(
        URLConstants.IMPORT_TRANSACTIONS,
        ImportTransactionsView.as_view(),
        name="import-transactions",
    ),
    path(
        URLConstants.RECATEGORIZE_TRANSACTIONS,
        RecategorizeTransactionsView.as_view(),
        name="recategorize-transactions",
    ),
    path(
        URLConstants.CREATE_KEYWORDS,
        CreateKeywordView.as_view(),
        name="create-keyword",
    ),
    path(
        URLConstants.DELETE_KEYWORDS,
        DeleteKeywordsView.as_view(),
        name="delete-keywords",
    ),
    path(
        URLConstants.CREATE_CATEGORY,
        CreateCategoryView.as_view(),
        name="create-category",
    ),
    path(
        URLConstants.DELETE_CATEGORIES,
        DeleteCategoriesView.as_view(),
        name="delete-categories",
    ),
    path(
        URLConstants.CREATE_SUBCATEGORY,
        CreateSubcategoryView.as_view(),
        name="create-subcategory",
    ),
    path(
        URLConstants.DELETE_SUBCATEGORIES,
        DeleteSubcategoriesView.as_view(),
        name="delete-subcategories",
    ),
    path(
        URLConstants.CREATE_BANK_ACCOUNT,
        CreateBankAccountView.as_view(),
        name="create-bank-account",
    ),
    path(
        URLConstants.DELETE_BANK_ACCOUNTS,
        DeleteBankAccountsView.as_view(),
        name="delete-bank-accounts",
    ),
    path(
        URLConstants.CREATE_CSV_MAPPING,
        CreateCSVMappingView.as_view(),
        name="create-csv-mapping",
    ),
    path(
        URLConstants.DELETE_CSV_MAPPINGS,
        DeleteCSVMappingsView.as_view(),
        name="delete-csv-mappings",
    ),
    path(
        URLConstants.CREATE_TAG,
        CreateTagView.as_view(),
        name="create-tag",
    ),
    path(
        URLConstants.DELETE_TAGS,
        DeleteTagsView.as_view(),
        name="delete-tags",
    ),
]
