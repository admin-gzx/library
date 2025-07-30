from rest_framework import serializers
from .models import Book, Reader, BorrowRecord
from django.utils import timezone


class BookSerializer(serializers.ModelSerializer):
    """图书序列化器，处理图书数据的序列化和反序列化"""

    class Meta:
        model = Book
        fields = '__all__'  # 包含所有字段
        read_only_fields = ['created_at', 'updated_at']  # 这两个字段只读，不允许客户端修改

    def validate(self, data):
        """
        验证数据：确保可借数量不超过总藏书量
        """
        if data.get('available_copies', 0) > data.get('total_copies', 0):
            raise serializers.ValidationError("可借数量不能超过总藏书量")
        return data


class ReaderSerializer(serializers.ModelSerializer):
    """读者序列化器，处理读者数据的序列化和反序列化"""

    class Meta:
        model = Reader
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class BorrowRecordSerializer(serializers.ModelSerializer):
    """借阅记录序列化器，处理借阅数据的序列化和反序列化"""
    # 额外字段，用于在返回结果中显示图书和读者的名称
    book_title = serializers.CharField(source='book.title', read_only=True)
    reader_name = serializers.CharField(source='reader.name', read_only=True)

    class Meta:
        model = BorrowRecord
        fields = ['id', 'book', 'book_title', 'reader', 'reader_name',
                  'borrow_date', 'due_date', 'return_date', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'book_title', 'reader_name']

    def validate(self, data):
        """
        验证借阅数据：
        1. 确保借阅日期不晚于应还日期
        2. 确保借阅时图书可借数量大于0
        """
        # 验证借阅日期和应还日期的逻辑
        if data['borrow_date'] > data['due_date']:
            raise serializers.ValidationError("借阅日期不能晚于应还日期")

        # 如果是新借阅（不是更新操作），检查图书可借数量
        if self.instance is None and data['book'].available_copies <= 0:
            raise serializers.ValidationError(f"图书《{data['book'].title}》目前没有可借副本")

        return data


class BorrowReturnSerializer(serializers.Serializer):
    """还书操作专用序列化器，用于验证还书请求"""
    return_date = serializers.DateField(required=False, default=timezone.now().date())

    def validate_return_date(self, value):
        """验证还书日期不能早于借阅日期"""
        # 获取当前借阅记录实例
        borrow_record = self.context.get('borrow_record')
        if value < borrow_record.borrow_date:
            raise serializers.ValidationError("还书日期不能早于借阅日期")
        return value
