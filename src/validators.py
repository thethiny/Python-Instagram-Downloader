from typing import Dict, List, Literal, Optional, Tuple, TypedDict

class ParsedTagUserType(TypedDict):
    id: str
    username: str
class ParsedItemType(TypedDict):
    id: str
    owner: str
    owner_username: str
    tagged_users: List[ParsedTagUserType]
    parent: Optional[str]
    image_url: str
    video_url: Optional[str]
    besties_only: bool
    time: int

class UserType(TypedDict):
    pk: str
    id: str
    username: str
    full_name: str
    profile_pic_url_hd: Optional[str]
    profile_pic_url: str

class MediaCandidateType(TypedDict):
    width: int
    height: int
    url: str

class UserMediaTagType(TypedDict):
    user: UserType
    position: Tuple[float, float]
    start_time_in_video_in_sec: Optional[float]
    duration_in_video_in_sec: Optional[float]

class ReelItemType(TypedDict):
    pk: str
    id: str
    user: UserType
    carousel_parent_id: str
    audience: str
    image_versions2: Dict[Literal["candidates"], List[MediaCandidateType]]
    video_versions: List[MediaCandidateType]
    taken_at: int # TimeStamp
    usertags: Dict[str, List[UserMediaTagType]]

class ListUserType(TypedDict):
    sessionid: str
    users: List[str]

class ListObjectType(TypedDict):
    categories: Dict[str, ListUserType]
    sessionids: Dict[str, str]
