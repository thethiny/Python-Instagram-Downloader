import os
from typing import Dict, List, Literal, Optional, TypedDict
from src.consts import MEDIA_PATH

from src.utils import download_item, get_extension_from_url

class ParsedItemType(TypedDict):
    id: str
    owner: str
    parent: Optional[str]
    image_url: str
    video_url: Optional[str]
    besties_only: bool

class UserType(TypedDict):
    pk: str
    id: str
    profile_pic_url_hd: Optional[str]
    profile_pic_url: str

class MediaCandidateType(TypedDict):
    width: int
    height: int
    url: str

class ReelItemType(TypedDict):
    pk: str
    id: str
    user: UserType
    carousel_parent_id: str
    audience: str
    image_versions2: Dict[Literal["candidates"], List[MediaCandidateType]]
    video_versions: List[MediaCandidateType]

class ListObjectType(TypedDict):
    sessionid: str
    users: List[str]