import os
import pickle
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import DirectorySerializer, DirectoryCreateSerializer, FileSerializer, FileGetSerializer
from .models import Directory, File
from urllib.parse import unquote
import pandas as pd
from . utils import df_to_byte


class CreateDirectoryView(APIView):

    def post(self, request):

        serializer = DirectoryCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteDirectoryView(APIView):

    def delete(self, request, id):
        try:
            directory = Directory.objects.get(id=id)
            directory.delete()
            return Response({"message": f"El directorio '{id}' fue correctamente eliminado"},
                            status=status.HTTP_204_NO_CONTENT)
        except Directory.DoesNotExist:
            return Response({'error': f'El directorio {id} no existe'}, status=status.HTTP_404_NOT_FOUND)


class DeleteFileView(APIView):
    def delete(self, request, id):
        try:
            file = File.objects.get(id=id)
            file.delete()
            return Response({"message": f"El archivo '{id}' fue correctamente eliminado"},
                            status=status.HTTP_204_NO_CONTENT)
        except Directory.DoesNotExist:
            return Response({'error': f'El archivo {id} no existe'}, status=status.HTTP_404_NOT_FOUND)


class DataListView(APIView):
    def get(self, request):
        directories = Directory.objects.all()
        serializer = DirectorySerializer(directories, many=True)
        return Response(serializer.data)


class FullProcessView(APIView):

    def post(self, request):
        path = unquote(request.data['path'])
        extension = request.data['extension']
        data_frames = []
        name_directory = path.split('\\')[-1]

        if Directory.objects.filter(name=name_directory).exists():
            if Directory.objects.filter(name=name_directory, path=path).exists():
                directory = Directory.objects.get(name=name_directory)
            else:
                return Response({
                    'mssg': f"El directorio '{name_directory}' ya existe"},
                    status=status.HTTP_400_BAD_REQUEST)
        else:
            directory = Directory.objects.create(
                path=path,
                name=name_directory
            )

        try:
            files_in_directory = os.listdir(path)
        except FileNotFoundError as e:
            return Response({
                                'mssg': f"No se encontró el directorio '{name_directory}'",
                                'error': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        except OSError as e:
            return Response({
                'mssg': f"Hubo un problema al procesar el directorio '{name_directory}'",
                'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST)

        for file in files_in_directory:
            if file.endswith(extension) and not file.startswith('~$'):
                file_path = os.path.join(path, file)
                file_name = file.split('.')[0]

                if extension == '.csv':
                    df = pd.read_csv(file_path, parse_dates=['Time'], sep=';')
                elif extension == '.xlsx':
                    df = pd.read_excel(file_path, skiprows=1)
                else:
                    return Response({'error': f"El formato '{extension}' no es válido"},
                                    status=status.HTTP_400_BAD_REQUEST)

                try:
                    df['Time'] = pd.to_datetime(df['Time'], format='%d/%m/%Y %H:%M')
                    df['Time'] = (df['Time'] - pd.Timestamp("1970-01-01")
                                  ) // pd.Timedelta('1ms')
                except ValueError:
                    print(f"Error al convertir 'Time' a datetime en el archivo {file}")

                if not File.objects.filter(directory=directory, name=file_name).exists():
                    file_object = File.objects.create(
                        name=file_name,  # Faja1 010321.csv ['Faja1 010321','.csv']
                        data_frame=pickle.dumps(df_to_byte(df).read()),
                        directory=directory
                    )

                data_frames.append(df)

        try:
            new_df = pd.concat(data_frames, ignore_index=True)
        except ValueError as e:
            directory.delete()
            return Response({'error': f"Error al concatenar los archivos del directorio '{name_directory}'",
                             'mssg': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

        dict_df = new_df.to_dict(orient='records')

        response_data = {
            'directory_id': directory.id,
            'data_frames': dict_df,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class ConvertExcelToCsvView(APIView):

    def post(self, request):
        path = unquote(request.data['input_path'])
        csv_folder = unquote(request.data['output_path'])  # Ruta donde se guardarán los archivos CSV

        if not os.path.exists(csv_folder):
            os.makedirs(csv_folder)

        for file in os.listdir(path):
            if file.endswith('.xlsx'):
                file_path = os.path.join(path, file)
                csv_path = os.path.join(csv_folder, os.path.splitext(file)[0] + '.csv')

                try:
                    df = pd.read_excel(file_path, skiprows=1)

                    # Tu lógica de procesamiento adicional aquí si es necesario

                    df.to_csv(csv_path, index=False, sep=';')
                except Exception as e:
                    print(f"Error al procesar el archivo {file}: {str(e)}")

        return Response({'message': 'Archivos CSV generados con éxito'}, status=status.HTTP_200_OK)


class DataFilesInDirectoryView(APIView):
    def get(self, request, id):
        try:
            directory = Directory.objects.get(pk=id)
            files = File.objects.filter(directory=directory)
            data_frames = []

            for file in files:
                bytes_data_file = BytesIO(pickle.loads(file.data_frame))
                df = pd.read_pickle(bytes_data_file)
                data_frames.append(df)

            new_df = pd.concat(data_frames, ignore_index=True)
            new_df = new_df.sort_values(by=['Time'])
            dict_df = new_df.to_dict(orient='records')

            return Response(dict_df, status=status.HTTP_200_OK)
        except Directory.DoesNotExist:
            return Response({'error': 'Directorio no encontrado'}, status=status.HTTP_404_NOT_FOUND)


class ComparativeFileView(APIView):

    def post(self, request):
        array_id = request.data['array_id']

        data_frames_list = []

        for i in range(len(array_id)):
            tmp_df = obtain_data_frames(array_id[i])

            if tmp_df is not None:
                data_frames_list.append(tmp_df)

        if not data_frames_list:
            return Response({'error': 'No hay datos para comparar'}, status=status.HTTP_404_NOT_FOUND)

        concatenated_df = pd.concat(data_frames_list, ignore_index=True)
        grouped_data = concatenated_df.groupby('Time')

        result_df = grouped_data.agg({'UAvg': 'mean', 'IAvg': 'mean', 'PTotAvg': 'sum', 'EngAvg': 'sum', 'TN': 'mean'})

        result_df.reset_index(inplace=True)

        dict_df = result_df.to_dict(orient='records')

        return Response(dict_df, status=status.HTTP_200_OK)


def obtain_data_frames(id):

    try:
        directory = Directory.objects.get(pk=id)
        files = File.objects.filter(directory=directory)
        data_frames = []

        for file in files:
            bytes_data_file = BytesIO(pickle.loads(file.data_frame))
            df = pd.read_pickle(bytes_data_file)
            data_frames.append(df)

        new_df = pd.concat(data_frames, ignore_index=True)
        new_df = new_df.sort_values(by=['Time'])
        return new_df
    except:
        return None