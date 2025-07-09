import itertools
from datetime import date
from typing import Any, Iterable, TypedDict

from spodcat.time_period import TimePeriod
from spodcat.utils import date_to_timestamp_ms


class AbstractGraphData:
    class DataPoint(TypedDict):
        x: int
        y: float

    class DataSet(TypedDict):
        data: "list[AbstractGraphData.DataPoint]"
        label: str | None

    datasets: list[DataSet]

    def get_label(self, t: Any) -> Any:
        if t is None:
            return None
        if isinstance(t, tuple):
            return t[1]
        return t

    def get_x(self, d: dict) -> int:
        return d["x"]

    def get_y(self, d: dict) -> float:
        return d["y"]

    def group_queryset_by(self, d: dict) -> Any:
        return None


class GraphData(AbstractGraphData):
    def __init__(self, data: Iterable[dict]):
        self.datasets = []

        for key, values in itertools.groupby(data, key=self.group_queryset_by):
            self.datasets.append({
                "label": self.get_label(key),
                "data": [{
                    "x": self.get_x(v),
                    "y": self.get_y(v),
                } for v in values],
            })

    def fill_empty_points(self, points: Iterable[int]):
        for dataset in self.datasets:
            new_data: list[AbstractGraphData.DataPoint] = []
            datadict = {d["x"]: d["y"] for d in dataset["data"]}

            for x in points:
                new_data.append({"x": x, "y": datadict.get(x, 0)})

            dataset["data"] = new_data

        return self


class PeriodicalGraphData(AbstractGraphData):
    period_type: type[TimePeriod]
    raw_data: Iterable[dict]
    average: bool
    grouped: bool

    def __init__(
        self,
        data: Iterable[dict],
        period_type: type[TimePeriod],
        average: bool = False,
        grouped: bool = True,
    ):
        self.raw_data = data
        self.period_type = period_type
        self.average = average
        self.grouped = grouped

    def get_datasets(self, start_date: date, end_date: date) -> list[AbstractGraphData.DataSet]:
        start = self.period_type(start_date)
        end = self.period_type(end_date)
        datasets: list[AbstractGraphData.DataSet] = []

        for key, values in itertools.groupby(self.raw_data, key=self.group_queryset_by):
            datapoints: list[AbstractGraphData.DataPoint] = []
            raw_datapoints: list[AbstractGraphData.DataPoint] = [
                {"x": self.get_x(v), "y": self.get_y(v)} for v in values
            ]
            for period in start.range(end):
                datapoints.append(self.__collect_datapoint(raw_datapoints, period))
            datasets.append({"label": self.get_label(key), "data": list(self.__prune_datapoints(datapoints))})

        return datasets

    def get_x(self, d):
        if "date" in d:
            return date_to_timestamp_ms(d["date"])
        if "year" in d and "month" in d and "day" in d:
            return date_to_timestamp_ms(date(d["year"], d["month"], d["day"]))
        if "year" in d and "week" in d:
            return date_to_timestamp_ms(date.fromisocalendar(d["year"], d["week"], 1))
        if "year" in d and "month" in d:
            return date_to_timestamp_ms(date(d["year"], d["month"], 1))
        if "year" in d:
            return date_to_timestamp_ms(date(d["year"], 1, 1))
        raise ValueError()

    def group_queryset_by(self, d):
        if self.grouped:
            return (d["slug"], d["name"])
        return None

    def __collect_datapoint(
        self,
        datapoints: list[AbstractGraphData.DataPoint],
        period: TimePeriod,
    ) -> AbstractGraphData.DataPoint:
        points = [dp for dp in datapoints if period.start_timestamp <= dp["x"] < period.end_timestamp]
        y = sum((dp["y"] for dp in points), 0.0)

        if self.average and points:
            y = y / len(points)

        return {"x": period.start_timestamp, "y": y}

    def __prune_datapoints(self, points: list[AbstractGraphData.DataPoint]):
        for idx, point in enumerate(points):
            if (
                idx == 0 or
                idx >= len(points) - 1 or
                point["y"] != 0.0 or
                points[idx - 1]["y"] != 0.0 or
                points[idx + 1]["y"] != 0.0
            ):
                yield point
