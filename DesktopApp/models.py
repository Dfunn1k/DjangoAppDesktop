from django.db import models
from django_pandas.managers import DataFrameManager

# Create your models here.


class Directory(models.Model):
    path = models.CharField(max_length=255)
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} -> {self.path}"


class File(models.Model):
    name = models.CharField(max_length=50)
    data_frame = models.BinaryField()
    directory = models.ForeignKey(Directory, related_name='files',  on_delete=models.CASCADE)

    objects = DataFrameManager()

    def __str__(self):
        return f"{self.name}"
