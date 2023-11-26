from rest_framework import serializers
from .models import Directory, File


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'name']


class FileGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'


class DirectorySerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Directory
        fields = ['id', 'name', 'files']


class DirectoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Directory
        fields = '__all__'


