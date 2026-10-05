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
        lines = {item.id for item in self.transit}
        stray = [item.id for item in self.neighborhoods if not set(item.transit) <= lines]
        if stray:
            raise ValueError(f'Unknown transit lines named by {stray}.')
        return self


class Careers(Record):
    schema_version: Literal[1]
    source: Source
    careers: list[Career] = Field(min_length=10)
