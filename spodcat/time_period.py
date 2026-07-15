import datetime
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

from dateutil.relativedelta import relativedelta

from spodcat.utils import date_to_timestamp_ms


if TYPE_CHECKING:
    from typing import Generator


class TimePeriod(ABC):
    """
    A time period which is also anchored in absolute time. E.g. not just "a
    month", but "the month of August, 2024".

    Note that `start_date` is inclusive while `end_date` is exclusive, so
    `Month(date(2026, 7, 14))` will produce an object with
    `start_date == date(2026, 7, 1)` and `end_date == date(2026, 8, 1)`.
    """

    start_date: datetime.date
    end_date: datetime.date
    start_timestamp: int
    end_timestamp: int

    def __init__(self, start_date: datetime.date):
        self.start_date, self.end_date = self.construct_dates(start_date)
        self.start_timestamp = date_to_timestamp_ms(self.start_date)
        self.end_timestamp = date_to_timestamp_ms(self.end_date)

    @abstractmethod
    def __add__(self, other) -> Self: ...

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return other.start_date == self.start_date
        return False

    def __index__(self):
        return self.start_timestamp

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.start_date < other.start_date
        return NotImplemented

    @abstractmethod
    def __sub__(self, other) -> Self | int: ...

    @staticmethod
    @abstractmethod
    def construct_dates(start_date: datetime.date) -> tuple[datetime.date, datetime.date]: ...

    def range(self, stop: Self, inclusive: bool = True) -> "Generator[Self]":
        if stop > self:
            for i in range(stop - self):
                yield self + i
            if inclusive:
                yield stop
        elif stop == self and inclusive:
            yield self


class Day(TimePeriod):
    def __add__(self, other):
        if isinstance(other, int):
            return Day(self.start_date + relativedelta(days=other))
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            return Day(self.start_date - relativedelta(days=other))
        if isinstance(other, Day):
            return (self.start_date - other.start_date).days
        return NotImplemented

    @staticmethod
    def construct_dates(start_date: datetime.date):
        return start_date, start_date + relativedelta(days=1)


class Month(TimePeriod):
    def __add__(self, other):
        if isinstance(other, int):
            return Month(self.start_date + relativedelta(months=other))
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            return Month(self.start_date - relativedelta(months=other))
        if isinstance(other, Month):
            delta = relativedelta(self.start_date, other.start_date)
            return (delta.years * 12) + delta.months
        return NotImplemented

    @staticmethod
    def construct_dates(start_date: datetime.date):
        start_date = datetime.date(start_date.year, start_date.month, 1)
        return start_date, start_date + relativedelta(months=1)


class Week(TimePeriod):
    def __add__(self, other):
        if isinstance(other, int):
            return Week(self.start_date + relativedelta(weeks=other))
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            return Week(self.start_date - relativedelta(weeks=other))
        if isinstance(other, Week):
            return int((self.start_date - other.start_date).days / 7)
        return NotImplemented

    def construct_dates(self, start_date: datetime.date):
        year, week, _ = start_date.isocalendar()
        start_date = datetime.date.fromisocalendar(year, week, 1)
        return start_date, start_date + relativedelta(weeks=1)


class Year(TimePeriod):
    def __add__(self, other):
        if isinstance(other, int):
            return Year(self.start_date + relativedelta(years=other))
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            return Year(self.start_date - relativedelta(years=other))
        if isinstance(other, Year):
            return relativedelta(self.start_date, other.start_date).years
        return NotImplemented

    @staticmethod
    def construct_dates(start_date: datetime.date):
        start_date = datetime.date(start_date.year, 1, 1)
        return start_date, start_date + relativedelta(years=1)
