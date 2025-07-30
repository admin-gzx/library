from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, ReaderViewSet, BorrowRecordViewSet

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'books', BookViewSet)  # 图书相关API：/api/books/
router.register(r'readers', ReaderViewSet)  # 读者相关API：/api/readers/
router.register(r'borrows', BorrowRecordViewSet)  # 借阅相关API：/api/borrows/

# 应用的URL模式
urlpatterns = [
    path('', include(router.urls)),  # 包含所有注册的路由
]
