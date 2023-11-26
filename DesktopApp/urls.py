from django.urls import path
from .views import (CreateDirectoryView,
                    FullProcessView,
                    ConvertExcelToCsvView,
                    DeleteDirectoryView,
                    DeleteFileView,
                    DataListView,
                    DataFilesInDirectoryView)

app_name = 'DesktopApp'

urlpatterns = [
    path('api/create/directory/', CreateDirectoryView.as_view(), name='create_directory'),
    # path('api/create/file/')
    path('api/delete/directory/<id>/', DeleteDirectoryView.as_view(), name='delete_directory'),
    path('api/delete/file/<id>/', DeleteFileView.as_view(), name='delete_file'),
    path('api/convert_csv/', ConvertExcelToCsvView.as_view(), name='convert_to_csv'),
    path('api/full_process/', FullProcessView.as_view(), name='full_process'),
    path('api/get/data_list/', DataListView.as_view(), name='data_list'),
    path('api/get/data_directory/<id>/', DataFilesInDirectoryView.as_view(), name='data_directory')
]
