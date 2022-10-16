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

def download_list(downloads_list: List[ParsedItemType], mappings, folder):
    all_exist = True
    for i, item in enumerate(downloads_list):
        parent_id = item["parent"]
        id_ = item["id"]
        if parent_id:
            image_name = video_name = f"{parent_id}_{id_}"
        else:
            image_name = video_name = id_
        try:
            owner = mappings[str(item["owner"])]
        except KeyError:
            print("Uknown Owner", item["owner"])
            owner = os.path.join("Unknown", str(item["owner"]))
        print(f"Downloading item {id_} for {owner} ({i+1}/{len(downloads_list)})", end="\r")
        image = item["image_url"]
        video = item["video_url"]
        besties = item["besties_only"]
        image_ext = get_extension_from_url(image)
        video_ext = get_extension_from_url(video)
        path = os.path.join(MEDIA_PATH, owner, folder)
        os.makedirs(path, exist_ok=True)
        if besties:
            path = os.path.join(path, "private")

        thumbnails_path = os.path.join(path, "video_thumbnails")
        os.makedirs(thumbnails_path,exist_ok=True)

        if video:
            image_name = os.path.join("video_thumbnails", image_name + "_thumbnail")
            video_file = os.path.join(path, f"{video_name}.{video_ext}")
            if download_item(video, video_file):
                all_exist = False
        
        image_file = os.path.join(path, f"{image_name}.{image_ext}")
        if download_item(image, image_file):
            all_exist = False
    print()
    return all_exist