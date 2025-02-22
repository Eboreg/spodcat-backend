import math
from typing import BinaryIO, Generator

from pydub import AudioSegment


def get_audio_file_dbfs_array(file: BinaryIO, format_name: str) -> list[float]:
    dbfs_values = [-100.0 if s.dBFS < -100 else s.dBFS for s in split_audio_file(file, 200, format_name)]
    min_dbfs = min(dbfs_values)
    dbfs_values = [dbfs - min_dbfs for dbfs in dbfs_values]
    max_dbfs = max(dbfs_values)
    multiplier = 100 / max_dbfs

    return [dbfs * multiplier for dbfs in dbfs_values]


def split_audio_file(file: BinaryIO, parts: int, format_name: str) -> Generator[AudioSegment, None, None]:
    whole = AudioSegment.from_file(file, format_name)
    i = 0
    n = math.ceil(len(whole) / parts)

    while i < len(whole):
        yield whole[i:i + n]
        i += n
