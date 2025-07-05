import itertools
from datetime import date, timedelta
from typing import TYPE_CHECKING, Iterable, TypedDict

from spodcat.utils import Month, date_to_timestamp_ms


if TYPE_CHECKING:
    class DailyChartQuerySetValues(TypedDict):
        date: date
        name: str
        slug: str
        y: float

    class MonthlyChartQuerySetValues(TypedDict):
        month: int
        name: str
        slug: str
        y: float
        year: int


class ChartData:
    class DataSet(TypedDict):
        class DataPoint(TypedDict):
            x: int
            y: float

        data: list[DataPoint]
        label: str

    datasets: list[DataSet]

    @property
    def max_x(self):
        return max(d["x"] for dataset in self.datasets for d in dataset["data"])

    @property
    def min_x(self):
        return min(d["x"] for dataset in self.datasets for d in dataset["data"])

    def __init__(self):
        self.datasets = []


class MonthChartData(ChartData):
    def __init__(self, data: Iterable["MonthlyChartQuerySetValues"], start_date: date, end_date: date):
        super().__init__()
        self.start = Month.from_date(start_date)
        self.end = Month.from_date(end_date)

        for key, values in itertools.groupby(data, key=lambda v: tuple([v["slug"], v["name"]])):
            self.datasets.append({
                "label": key[1],
                "data": [{
                    "x": Month(year=v["year"], month=v["month"]).timestamp_ms,
                    "y": v["y"]
                } for v in values],
            })

    def fill_empty_points(self):
        for dataset in self.datasets:
            new_data: list[ChartData.DataSet.DataPoint] = []
            datadict = {d["x"]: d["y"] for d in dataset["data"]}

            for month in self.start.range_until(self.end):
                new_data.append({"x": month.timestamp_ms, "y": datadict.get(month.timestamp_ms, 0)})

            dataset["data"] = new_data

        return self


class DailyChartData(ChartData):
    end_date: date
    start_date: date

    def __init__(self, data: Iterable["DailyChartQuerySetValues"], start_date: date, end_date: date):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date

        for key, values in itertools.groupby(data, key=lambda v: tuple([v["slug"], v["name"]])):
            self.datasets.append({
                "label": key[1],
                "data": [{"x": date_to_timestamp_ms(v["date"]), "y": v["y"]} for v in values],
            })

    def fill_empty_points(self):
        days = (self.end_date - self.start_date).days + 1
        dates = [date_to_timestamp_ms(self.start_date + timedelta(days=d)) for d in range(days)]

        for dataset in self.datasets:
            new_data: list[ChartData.DataSet.DataPoint] = []
            datadict = {d["x"]: d["y"] for d in dataset["data"]}
            for d in dates:
                new_data.append({"x": d, "y": datadict.get(d, 0)})
            dataset["data"] = new_data

        return self
