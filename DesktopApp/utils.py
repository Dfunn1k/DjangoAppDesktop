from io import BytesIO
from pandas import DataFrame


def df_to_byte(df: DataFrame) -> BytesIO:
    bytes_data = BytesIO()
    df.to_pickle(bytes_data)
    bytes_data.seek(0)
    return bytes_data
