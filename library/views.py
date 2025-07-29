from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
import json

from .models import Book, Reader, BorrowRecord
from .serializers import BookSerializer, ReaderSerializer, BorrowRecordSerializer
from django.conf import settings

# Redis缓存前缀
CACHE_PREFIX = 'library:'


class BookViewSet(viewsets.ModelViewSet):
    """图书视图集，提供CRUD操作"""
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'publisher']
    search_fields = ['title', 'author', 'isbn']
    ordering_fields = ['title', 'publication_date', 'created_at']

    def list(self, request, *args, **kwargs):
        """列表查询，使用Redis缓存结果"""
        cache_key = f"{CACHE_PREFIX}books:list"

        # 检查缓存
        cached_data = settings.REDIS_CONNECTION.get(cache_key)
        if cached_data:
            return Response(json.loads(cached_data))

        # 缓存未命中，查询数据库
        response = super().list(request, *args, **kwargs)

        # 存入缓存，设置过期时间10分钟
        settings.REDIS_CONNECTION.setex(cache_key, 600, json.dumps(response.data))

        return response

    def retrieve(self, request, *args, **kwargs):
        """详情查询，使用Redis缓存结果"""
        book_id = kwargs.get('pk')
        cache_key = f"{CACHE_PREFIX}books:{book_id}"

        # 检查缓存
        cached_data = settings.REDIS_CONNECTION.get(cache_key)
        if cached_data:
            return Response(json.loads(cached_data))

        # 缓存未命中，查询数据库
        response = super().retrieve(request, *args, **kwargs)

        # 存入缓存，设置过期时间10分钟
        settings.REDIS_CONNECTION.setex(cache_key, 600, json.dumps(response.data))

        return response

    def create(self, request, *args, **kwargs):
        """创建图书，清除相关缓存"""
        response = super().create(request, *args, **kwargs)

        # 清除列表缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:list")

        return response

    def update(self, request, *args, **kwargs):
        """更新图书，清除相关缓存"""
        book_id = kwargs.get('pk')
        response = super().update(request, *args, **kwargs)

        # 清除相关缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:list")
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:{book_id}")

        return response

    def destroy(self, request, *args, **kwargs):
        """删除图书，清除相关缓存"""
        book_id = kwargs.get('pk')
        response = super().destroy(request, *args, **kwargs)

        # 清除相关缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:list")
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:{book_id}")

        return response


class ReaderViewSet(viewsets.ModelViewSet):
    """读者视图集，提供CRUD操作"""
    queryset = Reader.objects.all()
    serializer_class = ReaderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'reader_id', 'email']
    ordering_fields = ['name', 'registration_date']

    def list(self, request, *args, **kwargs):
        """列表查询，使用Redis缓存结果"""
        cache_key = f"{CACHE_PREFIX}readers:list"

        # 检查缓存
        cached_data = settings.REDIS_CONNECTION.get(cache_key)
        if cached_data:
            return Response(json.loads(cached_data))

        # 缓存未命中，查询数据库
        response = super().list(request, *args, **kwargs)

        # 存入缓存，设置过期时间10分钟
        settings.REDIS_CONNECTION.setex(cache_key, 600, json.dumps(response.data))

        return response

    def retrieve(self, request, *args, **kwargs):
        """详情查询，使用Redis缓存结果"""
        reader_id = kwargs.get('pk')
        cache_key = f"{CACHE_PREFIX}readers:{reader_id}"

        # 检查缓存
        cached_data = settings.REDIS_CONNECTION.get(cache_key)
        if cached_data:
            return Response(json.loads(cached_data))

        # 缓存未命中，查询数据库
        response = super().retrieve(request, *args, **kwargs)

        # 存入缓存，设置过期时间10分钟
        settings.REDIS_CONNECTION.setex(cache_key, 600, json.dumps(response.data))

        return response

    def create(self, request, *args, **kwargs):
        """创建读者，清除相关缓存"""
        response = super().create(request, *args, **kwargs)

        # 清除列表缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}readers:list")

        return response

    def update(self, request, *args, **kwargs):
        """更新读者，清除相关缓存"""
        reader_id = kwargs.get('pk')
        response = super().update(request, *args, **kwargs)

        # 清除相关缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}readers:list")
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}readers:{reader_id}")

        return response

    def destroy(self, request, *args, **kwargs):
        """删除读者，清除相关缓存"""
        reader_id = kwargs.get('pk')
        response = super().destroy(request, *args, **kwargs)

        # 清除相关缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}readers:list")
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}readers:{reader_id}")

        return response


class BorrowRecordViewSet(viewsets.ModelViewSet):
    """借阅记录视图集，提供CRUD操作"""
    queryset = BorrowRecord.objects.all()
    serializer_class = BorrowRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['book', 'reader', 'return_date']
    ordering_fields = ['borrow_date', 'due_date', 'return_date']

    def create(self, request, *args, **kwargs):
        """创建借阅记录，同时更新图书可借数量"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book_id = request.data.get('book')
        try:
            book = Book.objects.get(id=book_id)

            # 检查是否有可借副本
            if book.available_copies <= 0:
                return Response(
                    {"error": "该图书已无可用副本"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 减少可借数量
            book.available_copies -= 1
            book.save()

            # 保存借阅记录
            self.perform_create(serializer)

            # 清除相关缓存
            settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:list")
            settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:{book_id}")

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )

        except Book.DoesNotExist:
            return Response(
                {"error": "图书不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        """处理还书操作"""
        borrow_record = self.get_object()

        # 如果已经归还，返回错误
        if borrow_record.return_date:
            return Response(
                {"error": "该图书已归还"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新归还日期
        from django.utils import timezone
        borrow_record.return_date = timezone.now()
        borrow_record.save()

        # 增加可借数量
        book = borrow_record.book
        book.available_copies += 1
        book.save()

        # 清除相关缓存
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:list")
        settings.REDIS_CONNECTION.delete(f"{CACHE_PREFIX}books:{book.id}")

        return Response({
            "message": "还书成功",
            "data": self.get_serializer(borrow_record).data
        })
