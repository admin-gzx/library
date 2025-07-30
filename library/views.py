from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.core.cache import cache
from .models import Book, Reader, BorrowRecord
from .serializers import (
    BookSerializer, ReaderSerializer, BorrowRecordSerializer,
    BorrowReturnSerializer
)


class BookViewSet(viewsets.ModelViewSet):
    """
    图书视图集，提供图书的CRUD操作
    支持搜索和缓存功能
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'publisher']  # 支持按类别和出版社过滤
    search_fields = ['title', 'author', 'isbn']  # 支持按书名、作者、ISBN搜索
    ordering_fields = ['title', 'publication_date', 'created_at']  # 支持排序的字段

    def get_queryset(self):
        """
        重写查询集方法，添加缓存功能
        热门查询结果会被缓存，提高性能
        """
        # 获取查询参数
        search = self.request.query_params.get('search', '')
        category = self.request.query_params.get('category', '')
        ordering = self.request.query_params.get('ordering', '')

        # 生成缓存键
        cache_key = f"books_search_{search}_category_{category}_order_{ordering}"

        # 尝试从缓存获取数据
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        # 缓存未命中，从数据库查询
        queryset = super().get_queryset()

        # 缓存结果，设置10分钟过期
        cache.set(cache_key, queryset, 600)
        return queryset


class ReaderViewSet(viewsets.ModelViewSet):
    """
    读者视图集，提供读者的CRUD操作
    """
    queryset = Reader.objects.all()
    serializer_class = ReaderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']  # 支持按账号状态过滤
    search_fields = ['name', 'reader_id', 'email']  # 支持按姓名、读者ID、邮箱搜索
    ordering_fields = ['name', 'registration_date']  # 支持排序的字段


class BorrowRecordViewSet(viewsets.ModelViewSet):
    """
    借阅记录视图集，提供借阅记录的CRUD操作
    额外提供还书功能
    """
    queryset = BorrowRecord.objects.all()
    serializer_class = BorrowRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['book', 'reader', 'return_date']  # 支持过滤的字段
    ordering_fields = ['borrow_date', 'due_date', 'return_date']  # 支持排序的字段

    def perform_create(self, serializer):
        """
        重写创建方法，处理借阅业务逻辑：
        1. 创建借阅记录
        2. 减少图书可借数量
        """
        # 保存借阅记录
        borrow_record = serializer.save()

        # 获取对应的图书并减少可借数量
        book = borrow_record.book
        book.available_copies -= 1
        book.save()

        # 清除相关缓存，确保数据一致性
        cache.delete_pattern("books_*")

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        """
        还书操作接口
        路径: /api/borrows/{id}/return_book/
        """
        # 获取借阅记录
        borrow_record = self.get_object()

        # 检查是否已经归还
        if borrow_record.return_date is not None:
            return Response(
                {"error": "这本书已经归还了"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 验证还书数据
        serializer = BorrowReturnSerializer(
            data=request.data,
            context={'borrow_record': borrow_record}
        )
        serializer.is_valid(raise_exception=True)

        # 更新借阅记录的归还日期
        borrow_record.return_date = serializer.validated_data['return_date']
        borrow_record.save()

        # 增加图书可借数量
        book = borrow_record.book
        book.available_copies += 1
        book.save()

        # 清除相关缓存
        cache.delete_pattern("books_*")

        return Response({
            "message": "还书成功",
            "return_date": borrow_record.return_date
        })
