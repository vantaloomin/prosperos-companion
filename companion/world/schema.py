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
                    'restaurant', 'cafe', 'bar', 'nightlife', 'fitness', 'library', 'trail']
Setting = Literal['indoor', 'outdoor', 'mixed']
Tier = Literal['low', 'mid', 'high', 'very-high']
Level = Literal['low', 'medium', 'high']
CollegeType = Literal['research-university', 'public-university', 'private-university', 'liberal-arts-college',
                      'community-college', 'art-school', 'medical-school', 'technical-institute', 'music-school']
Size = Literal['small', 'medium', 'large']
TransitKind = Literal['subway', 'light-rail', 'commuter-rail', 'bus', 'ferry', 'water-taxi', 'monorail',
                      'streetcar', 'bike-share', 'car', 'rideshare', 'walk']
ScheduleKind = Literal['office', 'shift-day', 'shift-night', 'rotating', 'evening', 'early', 'flexible', 'academic']


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Source(Record):
    kind: Literal['curated', 'wikidata', 'openstreetmap', 'government', 'other']
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
    rent_tier: Tier
    rent: Rent
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
    setting: Setting
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


class City(Record):
    schema_version: Literal[1]
    id: Id
    name: Text
    region: Text
    country: Literal['US']
    timezone: Text
    aliases: list[str] = Field(default_factory=list)
    summary: Text
    lat: float
    lon: float
    # Typical urban door-to-door speeds in km/h for commute estimates.
    speeds: dict[TransitKind, float]
    sources: dict[Id, Source]
    neighborhoods: list[Neighborhood] = Field(min_length=6)
    places: list[Place] = Field(min_length=20)
    colleges: list[College] = Field(min_length=3)
    employers: list[Employer] = Field(min_length=8)
    career_hubs: list[CareerHub] = Field(min_length=2)
    transit: list[TransitLine] = Field(min_length=1)
    climate: Climate
    annual_events: list[AnnualEvent] = Field(default_factory=list)

    @model_validator(mode='after')
    def check(self):
        groups = (self.neighborhoods, self.places, self.colleges, self.employers, self.career_hubs, self.transit,
                  self.annual_events)
        records = [item for group in groups for item in group]
        ids = [item.id for item in records]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate ids {sorted({i for i in ids if ids.count(i) > 1})}.')
        cited = [(item.id, item.source) for item in records] + [('climate', self.climate.source)]
        missing = [name for name, source in cited if source not in self.sources]
        if missing:
            raise ValueError(f'Unknown sources cited by {missing}.')
        hoods = {item.id for item in self.neighborhoods}
        located = [(item.id, {item.neighborhood}) for item in [*self.places, *self.colleges, *self.employers]]
        located += [(item.id, {item.neighborhood} - {None}) for item in self.annual_events]
        located += [(item.id, set(item.neighborhoods)) for item in self.career_hubs]
        stray = [name for name, used in located if not used <= hoods]
        if stray:
            raise ValueError(f'Unknown neighborhoods named by {stray}.')
        lines = {item.id for item in self.transit}
        stray = [item.id for item in self.neighborhoods if not set(item.transit) <= lines]
        if stray:
            raise ValueError(f'Unknown transit lines named by {stray}.')
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


class Careers(Record):
    schema_version: Literal[1]
    source: Source
    careers: list[Career] = Field(min_length=10)
