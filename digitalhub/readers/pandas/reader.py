from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd
from pandas.errors import ParserError

from digitalhub.entities.dataitem.table.utils import check_preview_size, finalize_preview, prepare_data, prepare_preview
from digitalhub.readers._base.reader import DataframeReader
from digitalhub.readers.pandas.enums import Extensions
from digitalhub.utils.exceptions import ReaderError
from digitalhub.utils.generic_utils import CustomJsonEncoder


class DataframeReaderPandas(DataframeReader):
    """
    Pandas reader class.
    """

    ##############################
    # Read methods
    ##############################

    def read_df(self, path: str | list[str], extension: str, **kwargs) -> pd.DataFrame:
        """
        Read DataFrame from path.

        Parameters
        ----------
        path : str | list[str]
            Path(s) to read DataFrame from.
        extension : str
            Extension of the file.
        **kwargs : dict
            Keyword arguments.

        Returns
        -------
        pd.DataFrame
            Pandas DataFrame.
        """
        if extension == Extensions.CSV.value:
            method = pd.read_csv
        elif extension == Extensions.PARQUET.value:
            method = pd.read_parquet
        elif extension == Extensions.JSON.value:
            method = pd.read_json
        elif extension in (Extensions.EXCEL.value, Extensions.EXCEL_OLD.value):
            method = pd.read_excel
        elif extension in (Extensions.TXT.value, Extensions.FILE.value):
            try:
                return self.read_df(path, Extensions.CSV.value, **kwargs)
            except ParserError:
                raise ReaderError(f"Unable to read from {path}.")
        else:
            raise ReaderError(f"Unsupported extension '{extension}' for reading.")

        if isinstance(path, list):
            dfs = [method(p, **kwargs) for p in path]
            return pd.concat(dfs)
        return method(path, **kwargs)

    ##############################
    # Write methods
    ##############################

    def write_df(
        self,
        df: pd.DataFrame,
        dst: str | BytesIO,
        extension: str | None = None,
        **kwargs,
    ) -> None:
        """
        Write DataFrame as parquet.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to write.
        dst : str | BytesIO
            The destination of the dataframe.
        **kwargs : dict
            Keyword arguments.

        Returns
        -------
        None
        """
        if extension == Extensions.CSV.value:
            return self.write_csv(df, dst, **kwargs)
        elif extension == Extensions.PARQUET.value:
            return self.write_parquet(df, dst, **kwargs)
        raise ReaderError(f"Unsupported extension '{extension}' for writing.")

    @staticmethod
    def write_csv(df: pd.DataFrame, dst: str | BytesIO, **kwargs) -> None:
        """
        Write DataFrame as csv.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to write.
        dst : str | BytesIO
            The destination of the dataframe.
        **kwargs : dict
            Keyword arguments.

        Returns
        -------
        None
        """
        df.to_csv(dst, index=False, **kwargs)

    @staticmethod
    def write_parquet(df: pd.DataFrame, dst: str | BytesIO, **kwargs) -> None:
        """
        Write DataFrame as parquet.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to write.
        dst : str | BytesIO
            The destination of the dataframe.
        **kwargs : dict
            Keyword arguments.

        Returns
        -------
        None
        """
        df.to_parquet(dst, index=False, **kwargs)

    @staticmethod
    def write_table(df: pd.DataFrame, table: str, engine: Any, schema: str, **kwargs) -> None:
        """
        Write DataFrame as table.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to write.
        table : str
            The destination table.
        engine : Any
            The SQLAlchemy engine.
        schema : str
            The destination schema.
        **kwargs : dict
            Keyword arguments.

        Returns
        -------
        None
        """
        df.to_sql(table, engine, schema=schema, index=False, **kwargs)

    ##############################
    # Utils
    ##############################

    @staticmethod
    def get_schema(df: pd.DataFrame) -> Any:
        """
        Get schema.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe.

        Returns
        -------
        Any
            The schema.
        """
        schema = {"fields": []}

        for column_name, dtype in df.dtypes.items():
            field = {"name": str(column_name), "type": ""}

            if pd.api.types.is_integer_dtype(dtype):
                field["type"] = "integer"
            elif pd.api.types.is_float_dtype(dtype):
                field["type"] = "number"
            elif pd.api.types.is_bool_dtype(dtype):
                field["type"] = "boolean"
            elif pd.api.types.is_string_dtype(dtype):
                field["type"] = "string"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                field["type"] = "datetime"
            else:
                field["type"] = "any"

            schema["fields"].append(field)

        return schema

    @staticmethod
    def get_preview(df: pd.DataFrame) -> dict:
        """
        Get preview.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe.

        Returns
        -------
        Any
            The preview.
        """
        columns = [str(col) for col, _ in df.dtypes.items()]
        head = df.head(10).replace({np.nan: None})
        data = head.values.tolist()
        prepared_data = prepare_data(data)
        preview = prepare_preview(columns, prepared_data)
        finalizes = finalize_preview(preview, df.shape[0])
        serialized = _serialize_deserialize_preview(finalizes)
        return check_preview_size(serialized)


class PandasJsonEncoder(CustomJsonEncoder):
    """
    JSON pd.Timestamp to ISO format serializer.
    """

    def default(self, obj: Any) -> Any:
        """
        Pandas datetime to ISO format serializer.

        Parameters
        ----------
        obj : Any
            The object to serialize.

        Returns
        -------
        Any
            The serialized object.
        """
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)


def _serialize_deserialize_preview(preview: dict) -> dict:
    """
    Serialize and deserialize preview.

    Parameters
    ----------
    preview : dict
        The preview.

    Returns
    -------
    dict
        The serialized preview.
    """
    return json.loads(json.dumps(preview, cls=PandasJsonEncoder))
