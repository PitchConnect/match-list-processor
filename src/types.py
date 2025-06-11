"""Type definitions for the match list processor."""

from typing import Dict, List, Optional, Any, Union
from typing_extensions import TypedDict


class RefereeDict(TypedDict, total=False):
    """Type definition for referee data."""
    domarid: Optional[int]
    personnamn: Optional[str]
    namn: Optional[str]
    domarrollnamn: Optional[str]


class MatchDict(TypedDict, total=False):
    """Type definition for match data."""
    matchid: int
    lag1namn: str
    lag2namn: str
    lag1lagid: int
    lag2lagid: int
    lag1foreningid: int
    lag2foreningid: int
    speldatum: str
    avsparkstid: str
    tid: str
    tidsangivelse: str
    tavlingnamn: str
    anlaggningnamn: str
    anlaggningid: int
    matchnr: str
    domaruppdraglista: List[RefereeDict]


class UploadResult(TypedDict):
    """Type definition for upload operation results."""
    status: str
    message: Optional[str]
    file_url: Optional[str]


class ProcessingResult(TypedDict, total=False):
    """Type definition for match processing results."""
    description_url: Optional[str]
    group_info_url: Optional[str]
    avatar_url: Optional[str]
    success: bool
    error_message: Optional[str]


# Type aliases
MatchId = int
MatchList = List[MatchDict]
MatchDict_Dict = Dict[MatchId, MatchDict]
FilePath = str
ServiceUrl = str
