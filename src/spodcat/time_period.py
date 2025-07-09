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
    """
    start_date: datetime.date
    end_date: datetime.date
    __start_timestamp: int
    __end_timestamp: int

    @property
    def start_timestamp(self):
        if not hasattr(self, "__start_timestamp"):
            self.__start_timestamp = date_to_timestamp_ms(self.start_date)
        return self.__start_timestamp

    @property
    def end_timestamp(self):
        if not hasattr(self, "__end_timestamp"):
            self.__end_timestamp = date_to_timestamp_ms(self.end_date)
        return self.__end_timestamp

    @abstractmethod
    def __init__(self, start_date: datetime.date):
        ...

    @abstractmethod
    def __add__(self, other) -> Self:
        ...

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
    def __sub__(self, other) -> Self | int:
        ...

    def range(self, stop: Self, inclusive: bool = True) -> "Generator[Self]":
        if stop > self:
            for i in range(stop - self):
                yield self + i
            if inclusive:
                yield stop
        elif stop == self and inclusive:
            yield self


class Day(TimePeriod):
    def __init__(self, start_date: datetime.date):
        self.start_date = start_date
        self.end_date = self.start_date + relativedelta(days=1)

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


class Month(TimePeriod):
    def __init__(self, start_date: datetime.date):
        self.start_date = datetime.date(start_date.year, start_date.month, 1)
        self.end_date = self.start_date + relativedelta(months=1)

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


class Week(TimePeriod):
    def __init__(self, start_date: datetime.date):
        year, week, _ = start_date.isocalendar()
        self.start_date = datetime.date.fromisocalendar(year, week, 1)
        self.end_date = self.start_date + relativedelta(weeks=1)

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


class Year(TimePeriod):
    def __init__(self, start_date: datetime.date):
        self.start_date = datetime.date(start_date.year, 1, 1)
        self.end_date = self.start_date + relativedelta(years=1)

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
