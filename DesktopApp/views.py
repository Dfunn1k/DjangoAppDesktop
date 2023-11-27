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

        # data = {
        #     'path': request.data['path'],
        #     'name': unquote(request.data['path']).split('\\')[-1]
        # }
        # print(request.data)
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
        data_frames = []
        name_directory = path.split('\\')[-1]

        if not Directory.objects.filter(name=name_directory).exists():
            directory = Directory.objects.create(
                path=path,
                name=name_directory
            )
        else:
            directory = Directory.objects.get(name=name_directory)
            # return Response({'error': f"El directorio '{name_directory}' ya existe"},
            #                 status=status.HTTP_404_NOT_FOUND)

        try:
            for file in os.listdir(path):
                if file.endswith('.xlsx') and not file.startswith('~$'):
                    file_path = os.path.join(path, file)
                    file_name = file.split('.')[0]
                    df = pd.read_excel(file_path, skiprows=1)

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
        except Exception as e:
            directory.delete()
            return Response({'error': f"Error al procesar el directorio '{name_directory}'",
                             'mssg': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            new_df = pd.concat(data_frames, ignore_index=True)
        except ValueError as e:
            directory.delete()
            return Response({'error': f"Error al concatenar los archivos del directorio '{name_directory}'",
                             'mssg': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

        # new_df = new_df.sort_values(by=['Time'])

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

                    df.to_csv(csv_path, index=False)
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

    def get(self, request, id_1, id_2):
        try:
            column_1 = ['Time', 'UAvg1', 'IAvg1', 'PTotAvg1', 'EngAvg1', 'TN1']
            column_2 = ['Time', 'UAvg2', 'IAvg2', 'PTotAvg2', 'EngAvg2', 'TN2']
            first_df = obtain_data_frames(id_1, column_1)
            second_df = obtain_data_frames(id_2, column_2)
            df_combined = pd.DataFrame()

            df_combined['Time'] = first_df['Time']

            df_combined['UAvg'] = (first_df['UAvg1'] + second_df['UAvg2']) / 2
            df_combined['IAvg'] = (first_df['IAvg1'] + second_df['IAvg2']) / 2
            df_combined['PTotAvg'] = first_df['PTotAvg1'] + second_df['PTotAvg2']
            df_combined['EngAvg'] = first_df['EngAvg1'] + second_df['EngAvg2']
            df_combined['TN'] = (first_df['TN1'] + second_df['TN2']) / 2

            df_combined = df_combined.fillna(0)

            dict_df = df_combined.to_dict(orient='records')

            return Response(dict_df, status=status.HTTP_200_OK)
        except:
            return Response({'mssg': 'ok'}, status=status.HTTP_404_NOT_FOUND)



# ['Time', 'UAvg1', 'IAvg1', 'PTotAvg1', 'EngAvg1', 'TN1']
def obtain_data_frames(id, columns):

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
        new_df.columns = columns
        return new_df
    except:
        return None