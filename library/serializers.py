from rest_framework import serializers
from .models import Book, Reader, BorrowRecord


class BookSerializer(serializers.ModelSerializer):
    """图书序列化器"""

    class Meta:
        model = Book
        fields = '__all__'


class ReaderSerializer(serializers.ModelSerializer):
    """读者序列化器"""

    class Meta:
        model = Reader
        fields = '__all__'


class BorrowRecordSerializer(serializers.ModelSerializer):
    """借阅记录序列化器"""
    book_title = serializers.ReadOnlyField(source='book.title')
    reader_name = serializers.ReadOnlyField(source='reader.name')

    class Meta:
        model = BorrowRecord
        fields = '__all__'
        read_only_fields = ['book_title', 'reader_name']
