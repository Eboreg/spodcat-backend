import subprocess

from spodcat.mediainfo import mediainfo


def get_audio_file_dbfs_array(
    filename: str,
    duration_seconds: float | None = None,
    sample_rate: int | None = None,
) -> list[float]:
    if duration_seconds is None or sample_rate is None:
        info = mediainfo(filename)
        duration_seconds = float(info["duration"])
        sample_rate = int(info["sample_rate"])

    samples = int(sample_rate * duration_seconds / 200)
    args = [
        "ffmpeg",
        "-i",
        filename,
        "-af",
        f"asetnsamples={samples},astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(args, capture_output=True, check=True)
    rows = [row for row in proc.stdout.decode().split("\n") if row.startswith("lavfi.astats.Overall.RMS_level")]

    return normalize_dbfs_values([float(row.split("=")[-1]) for row in rows])


def normalize_dbfs_values(dbfs_values: list[float]) -> list[float]:
    min_dbfs = min(dbfs_values)
    dbfs_values = [dbfs - min_dbfs for dbfs in dbfs_values]
    max_dbfs = max(dbfs_values)
    multiplier = 100 / max_dbfs

    return [dbfs * multiplier for dbfs in dbfs_values]
