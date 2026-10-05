"""Shape of the shipped world data. Loading validates every file, so a broken record fails the tests.

Every record names a source from its file's `sources` table, so each fact can be traced to where it
came from, under which license, and when it was gathered.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1
Id = Annotated[str, Field(pattern=r'^[a-z0-9]+(-[a-z0-9]+)*$', max_length=80)]
Text = Annotated[str, Field(min_length=1, max_length=400)]
Cost = Literal['free', '$', '$$', '$$$', '$$$$']
Season = Literal['winter', 'spring', 'summer', 'fall']
Company = Literal['solo', 'friends', 'date', 'family', 'coworkers']
DayPart = Literal['morning', 'afternoon', 'evening', 'late']
PlaceKind = Literal['attraction', 'museum', 'park', 'beach', 'landmark', 'venue', 'stadium', 'market', 'shopping',
                    'restaurant', 'cafe', 'bar', 'nightlife', 'fitness', 'library', 'trail',
                    # Kinds for historical, fictional and original settings.
                    'tavern', 'inn', 'temple', 'guildhall', 'workshop', 'square', 'docks', 'garden']
Exposure = Literal['indoor', 'outdoor', 'mixed']
Tier = Literal['low', 'mid', 'high', 'very-high']
Level = Literal['low', 'medium', 'high']
CollegeType = Literal['research-university', 'public-university', 'private-university', 'liberal-arts-college',
                      'community-college', 'art-school', 'medical-school', 'technical-institute', 'music-school',
                      'academy', 'seminary', 'guild-school']
Size = Literal['small', 'medium', 'large']
TransitKind = Literal['subway', 'light-rail', 'commuter-rail', 'bus', 'ferry', 'water-taxi', 'monorail',
                      'streetcar', 'bike-share', 'car', 'rideshare', 'walk',
                      'carriage', 'horse', 'tram', 'airship', 'boat', 'stagecoach']
# What a city is: a real place, a well-known fictional setting, or an original one (built in or the user's own).
Setting = Literal['real', 'fictional', 'original']
Era = Literal['modern', 'victorian', 'medieval', 'fantasy', 'steampunk', 'frontier', 'future', 'other']
ScheduleKind = Literal['office', 'shift-day', 'shift-night', 'rotating', 'evening', 'early', 'flexible', 'academic']


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Source(Record):
    kind: Literal['curated', 'wikidata', 'openstreetmap', 'government', 'user', 'other']
    title: Text
    license: Text
    retrieved: Annotated[str, Field(pattern=r'^\d{4}-\d{2}-\d{2}$')]
    url: str = ''
    attribution: str = ''
    note: str = Field(default='', max_length=1000)


class Rent(Record):
    """Typical monthly asking rent ranges in US dollars. Estimates for fiction, not listings."""
    studio: tuple[int, int]
    one_bedroom: tuple[int, int]
    two_bedroom: tuple[int, int]

    @model_validator(mode='after')
    def check(self):
        for low, high in (self.studio, self.one_bedroom, self.two_bedroom):
            if not 0 < low <= high:
                raise ValueError('Rent ranges are positive and low to high.')
        return self


class Neighborhood(Record):
    id: Id
    name: Text
    summary: Text
    vibe: list[Id] = Field(min_length=1, max_length=8)
    # Approximate centre, for distances and commute estimates only.
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    rent_tier: Tier = 'mid'
    # None where the setting has no rent to speak of (Oz has no money).
    rent: Rent | None = None
    housing: list[Id] = Field(min_length=1, max_length=6)
    walkability: Level
    transit: list[Id] = Field(default_factory=list, max_length=8)
    source: Id


class Place(Record):
    id: Id
    name: Text
    kind: PlaceKind
    neighborhood: Id
    summary: Text
    tags: list[Id] = Field(default_factory=list, max_length=10)
    cost: Cost
    setting: Exposure
    good_for: list[Company] = Field(min_length=1)
    day_parts: list[DayPart] = Field(min_length=1)
    # Empty means all year.
    seasons: list[Season] = Field(default_factory=list)
    cuisine: str = Field(default='', max_length=60)
    source: Id


class College(Record):
    id: Id
    name: Text
    type: CollegeType
    neighborhood: Id
    size: Size
    known_for: list[Id] = Field(min_length=1, max_length=10)
    source: Id


class Employer(Record):
    id: Id
    name: Text
    sector: Id
    neighborhood: Id
    size: Size
    summary: Text
    careers: list[Id] = Field(min_length=1)
    source: Id


class CareerHub(Record):
    id: Id
    name: Text
    neighborhoods: list[Id] = Field(min_length=1)
    sectors: list[Id] = Field(min_length=1)
    summary: Text
    source: Id


class TransitLine(Record):
    id: Id
    name: Text
    kind: TransitKind
    summary: Text
    source: Id


class Month(Record):
    high_f: int
    low_f: int
    rain_days: int = Field(ge=0, le=31)
    note: str = Field(default='', max_length=200)


class Climate(Record):
    summary: Text
    months: list[Month] = Field(min_length=12, max_length=12)
    source: Id


class AnnualEvent(Record):
    id: Id
    name: Text
    months: list[int] = Field(min_length=1)
    neighborhood: Id | None = None
    summary: Text
    source: Id

    @model_validator(mode='after')
    def check(self):
        if any(month < 1 or month > 12 for month in self.months):
            raise ValueError('Months are 1 to 12.')
        return self


class Career(Record):
    id: Id
    name: Text
    sector: Id
    schedule: ScheduleKind
    pay: Cost
    summary: Text
    # Themes the life simulation may draw on for this work.
    themes: list[str] = Field(min_length=1, max_length=8)
    # Settings this career belongs to; a city offers the shared careers of its era plus its own.
    eras: list[Era] = Field(default_factory=lambda: ['modern'], min_length=1)


class Currency(Record):
    code: Annotated[str, Field(min_length=1, max_length=12)] = 'USD'
    symbol: Annotated[str, Field(max_length=8)] = '$'
    name: Annotated[str, Field(min_length=1, max_length=40)] = 'US dollars'


class NameGroup(Record):
    """Given and family names that commonly go together, for one heritage in one period."""
    feminine: list[Text] = Field(default_factory=list)
    masculine: list[Text] = Field(default_factory=list)
    neutral: list[Text] = Field(default_factory=list)
    family: list[Text] = Field(min_length=1)
    # In modern settings, the shares of given names drawn from each culture's popular names for the person's
    # birth year (given_names.json) instead of the lists above. `local` is the city's own country.
    cultures: dict[Id, float] = Field(default_factory=dict)

    @model_validator(mode='after')
    def check(self):
        if not (self.feminine or self.masculine or self.neutral):
            raise ValueError('A name group needs some given names.')
        return self


class CityNames(Record):
    """How a city names its residents: a shared bank (its era's by default), group weights, and its own groups."""
    bank: Id | None = None
    mix: dict[Id, float] = Field(default_factory=dict)
    groups: dict[Id, NameGroup] = Field(default_factory=dict)


class Holiday(Record):
    """One holiday, by exactly one rule: a fixed date, the nth weekday of a month, or days from Easter."""
    id: Id
    name: Text
    kind: Literal['public', 'observance', 'feast']
    summary: Text
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)
    # Monday is 0. `nth` counts from 1, or -1 for the last in the month.
    weekday: int | None = Field(default=None, ge=0, le=6)
    nth: int | None = Field(default=None, ge=-1, le=5)
    easter: int | None = Field(default=None, ge=-70, le=70)

    @model_validator(mode='after')
    def check(self):
        shapes = {
            'fixed': self.month is not None and self.day is not None and self.weekday is None and self.nth is None,
            'weekday': self.month is not None and self.day is None and self.weekday is not None
            and self.nth not in (None, 0),
            'easter': self.easter is not None and self.month is None,
        }
        if sum(shapes.values()) != 1 or (self.easter is not None and (self.weekday, self.nth) != (None, None)):
            raise ValueError(f'Holiday {self.id} needs one rule: month and day, month weekday and nth, or easter.')
        return self


class LocalColor(Record):
    """Something locals eat, drink, say, root for or do, so the model can mention it without inventing it."""
    id: Id
    name: Text
    kind: Literal['dish', 'drink', 'saying', 'custom', 'team', 'shop', 'other']
    summary: Text
    # Where it is easiest to find, when it is a thing found in particular places.
    places: list[Id] = Field(default_factory=list, max_length=6)
    seasons: list[Season] = Field(default_factory=list)
    source: Id


class Price(Record):
    """A typical price range for an everyday purchase, in the city's currency. Estimates for fiction."""
    id: Id
    item: Text
    low: float = Field(ge=0)
    high: float = Field(ge=0)
    # What the price is for, when it isn't obvious: "a pint", "one way", "a week's board".
    per: str = Field(default='', max_length=80)
    source: Id

    @model_validator(mode='after')
    def check(self):
        if self.low > self.high:
            raise ValueError(f'Price {self.id} runs low to high.')
        return self


class City(Record):
    """One city. Minimums are small so a user can start a city of their own with a neighborhood and a place."""
    schema_version: Literal[1]
    id: Id
    name: Text
    setting: Setting = 'real'
    era: Era = 'modern'
    # 'private' marks a personal city pack (for example fan fiction of owned settings): loaded from a local
    # folder, never shipped or committed.
    distribution: Literal['public', 'private'] = 'public'
    # For fictional settings: the work it draws on and why it may be shipped (for example, public domain).
    basis: str = Field(default='', max_length=400)
    region: Text
    country: Text
    # Used for display and as the suggested companion timezone; fictional cities borrow a real zone.
    timezone: Text
    aliases: list[str] = Field(default_factory=list)
    summary: Text
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    currency: Currency = Currency()
    rent_period: Literal['month', 'week'] = 'month'
    # Typical door-to-door speeds in km/h for commute estimates.
    speeds: dict[TransitKind, float] = Field(default_factory=lambda: {'walk': 4.5})
    sources: dict[Id, Source] = Field(min_length=1)
    neighborhoods: list[Neighborhood] = Field(min_length=1, max_length=200)
    places: list[Place] = Field(min_length=1, max_length=2000)
    colleges: list[College] = Field(default_factory=list, max_length=200)
    employers: list[Employer] = Field(default_factory=list, max_length=500)
    career_hubs: list[CareerHub] = Field(default_factory=list, max_length=100)
    transit: list[TransitLine] = Field(default_factory=list, max_length=100)
    climate: Climate | None = None
    annual_events: list[AnnualEvent] = Field(default_factory=list, max_length=200)
    # Careers particular to this city or its setting, beside the shared catalogue.
    careers: list[Career] = Field(default_factory=list, max_length=200)
    names: CityNames | None = None
    local_color: list[LocalColor] = Field(default_factory=list, max_length=100)
    prices: list[Price] = Field(default_factory=list, max_length=60)
    # A shared holiday calendar ('none' for no shared one); by default chosen from the era and country.
    calendar: Id | None = None
    # Holidays particular to this city, beside its calendar's.
    holidays: list[Holiday] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def check(self):
        groups = (self.neighborhoods, self.places, self.colleges, self.employers, self.career_hubs, self.transit,
                  self.annual_events)
        records = [item for group in groups for item in group]
        ids = [item.id for item in records]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate ids {sorted({i for i in ids if ids.count(i) > 1})}.')
        cited = [(item.id, item.source) for item in records]
        cited += [('climate', self.climate.source)] if self.climate else []
        cited += [(item.id, item.source) for item in [*self.local_color, *self.prices]]
        missing = [name for name, source in cited if source not in self.sources]
        if missing:
            raise ValueError(f'Unknown sources cited by {missing}.')
        hoods = {item.id for item in self.neighborhoods}
        located = [(item.id, {item.neighborhood}) for item in [*self.places, *self.colleges, *self.employers]]
        located += [(item.id, {item.neighborhood} - {None}) for item in self.annual_events]
        located += [(item.id, set(item.neighborhoods)) for item in self.career_hubs]
        stray = [f'{name} ({", ".join(sorted(used - hoods))})' for name, used in located if not used <= hoods]
        if stray:
            raise ValueError(f'Unknown neighborhoods named by {", ".join(stray)}.')
        known = {item.id for item in [*self.places, *self.neighborhoods]}
        stray = [item.id for item in self.local_color if not set(item.places) <= known]
        if stray:
            raise ValueError(f'Local colour names unknown places: {stray}.')
        lines = {item.id for item in self.transit}
        stray = [item.id for item in self.neighborhoods if not set(item.transit) <= lines]
        if stray:
            raise ValueError(f'Unknown transit lines named by {stray}.')
        return self


class Careers(Record):
    schema_version: Literal[1]
    source: Source
    careers: list[Career] = Field(min_length=10)


class EraNames(Record):
    bank: Id
    mix: dict[Id, float] = Field(default_factory=dict)


class Names(Record):
    schema_version: Literal[1]
    source: Source
    banks: dict[Id, dict[Id, NameGroup]] = Field(min_length=1)
    eras: dict[Era, EraNames]

    @model_validator(mode='after')
    def check(self):
        for era, entry in self.eras.items():
            groups = self.banks.get(entry.bank)
            if groups is None or not set(entry.mix) <= set(groups):
                raise ValueError(f'Era {era} names an unknown bank or group.')
        return self


class Cohort(Record):
    """The most popular given names for babies born in these years, most popular first."""
    start: int = Field(ge=1800, le=2100)
    end: int = Field(ge=1800, le=2100)
    estimate: bool
    feminine: list[Text] = Field(min_length=1)
    masculine: list[Text] = Field(min_length=1)


class Culture(Record):
    name: Text
    sources: list[Source] = Field(min_length=1)
    # Most common family names, most common first; empty when people take the city group's family names.
    surnames: list[Text] = Field(default_factory=list)
    cohorts: list[Cohort] = Field(min_length=1)


class InventedNames(Record):
    given: list[Text]
    family: list[Text]


class GivenNames(Record):
    schema_version: Literal[1]
    # Ages count back from this year, so a name never changes with the clock.
    present_year: int = Field(ge=1900, le=2100)
    cultures: dict[Id, Culture] = Field(min_length=1)
    # Country names (lower case) to the culture whose names are local there.
    countries: dict[str, Id]
    invented: InventedNames

    @model_validator(mode='after')
    def check(self):
        unknown = set(self.countries.values()) - set(self.cultures)
        if unknown:
            raise ValueError(f'Countries name unknown cultures: {sorted(unknown)}.')
        blocked = {word.casefold() for word in [*self.invented.given, *self.invented.family]}
        for key, culture in self.cultures.items():
            words = {word.casefold() for cohort in culture.cohorts for word in [*cohort.feminine, *cohort.masculine]}
            words |= {word.casefold() for word in culture.surnames}
            if clash := words & blocked:
                raise ValueError(f'{key} lists invented-sounding names: {sorted(clash)}.')
        return self


class HolidayCalendar(Record):
    name: Text
    holidays: list[Holiday] = Field(min_length=1)


class Holidays(Record):
    schema_version: Literal[1]
    source: Source
    calendars: dict[Id, HolidayCalendar] = Field(min_length=1)


class Opening(Record):
    first: list[Text] = Field(min_length=1)
    second: list[Text] = Field(min_length=1)
    summary: Text


class Roadworks(Record):
    summary: Text
    # Extra minutes a trip by road through the works takes.
    delay: int = Field(ge=1, le=60)


class ChangeStyle(Record):
    openings: dict[PlaceKind, Opening] = Field(min_length=1)
    renovation: list[Text] = Field(min_length=1)
    closing: list[Text] = Field(min_length=1)
    roadworks: list[Roadworks] = Field(min_length=1)


class Changes(Record):
    schema_version: Literal[1]
    source: Source
    styles: dict[Id, ChangeStyle] = Field(min_length=1)
    eras: dict[Era, Id]

    @model_validator(mode='after')
    def check(self):
        missing = sorted(set(Era.__args__) - set(self.eras))
        unknown = sorted(set(self.eras.values()) - set(self.styles))
        if missing or unknown:
            raise ValueError(f'Every era needs a known style (missing {missing}, unknown {unknown}).')
        return self
