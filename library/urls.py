from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, ReaderViewSet, BorrowRecordViewSet

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'readers', ReaderViewSet)
router.register(r'borrows', BorrowRecordViewSet)

# API URL配置
urlpatterns = [
    path('', include(router.urls)),
]
