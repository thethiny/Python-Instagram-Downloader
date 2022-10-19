import json
import os
import shutil
from typing import Dict, Iterable, List, Optional

import requests

from src.consts import (FEED_API, IG_HEADERS, PROFILE_INFO_GRAPH_API,
                        STORY_API, USER_ID_API)
from src.utils import download_item, get_extension_from_url, set_creation_time
from src.validators import ParsedItemType, ParsedTagUserType, ReelItemType, UserMediaTagType, UserType


class InstagramDownloader:
    def __init__(self, sessionid):
        self.__init_session__(sessionid)

    def __init_session__(self, sessionid):
        self.session = requests.Session()
        self.session.cookies.set("sessionid", sessionid, domain=".instagram.com", path="/")

    def _get_request(self, url):
        return self.session.get(url, headers=IG_HEADERS)

    def get_user_profile(self, username: str):
        r = self._get_request(USER_ID_API.format(username=username))
        user: UserType = r.json()["data"]["user"]
        return user

    def get_reels_data(self, reel_ids: Iterable[str]):
        url = STORY_API.format(ids_string='&reel_ids='.join(reel_ids))
        r = self._get_request(url)
        return r.json()

    def parse_reels_data(self, data, known_mappings):
        for reel in data["reels"].values():
            user_id = reel_id = reel["id"]
            username = known_mappings.get(str(user_id), "Unknown")

            print("Parsing stories for", username)

            items: List[ReelItemType] = reel["items"]
            story_data = []
            for item in items:
                story_item = self.parse_reel_item(item)
                story_data.append(story_item)
            
            yield story_data, user_id

    def parse_highlights_data(self, data):
        for item in data:
            yield self.parse_reel_item(item)

    def get_all_posts_data(self, user_id):
        yield from self.get_posts_data(user_id, [])

    def get_posts_data(self, user_id, old_posts = []):
        next_id = ""
        has_more = True
        posts_count = 0

        old_posts = {p["id"] for p in old_posts}

        ctr = 1

        while has_more:
            print(f"Getting page {ctr} of posts", end = "")
            url = FEED_API.format(
                user_id=user_id,
                count=posts_count or 1,
                last_post_id=next_id,
            )
            r = self._get_request(url)
            data = r.json()

            has_more = data.get("more_available", False)
            print(" with more to come" if has_more else "")
            next_id = data.get("next_max_id", "")
            if not posts_count:
                posts_count = 50

            done = False
            for item in data["items"]:
                item_id = item["pk"]
                if item_id in old_posts:
                    done = True
                    break
                yield item
            ctr += 1
            if done:
                break

    def parse_posts_data(self, posts):
        for item in posts:
            post_items = self.parse_post_item(item)
            if not post_items:
                continue
            yield post_items
            

    def get_highlights_data(self, user_id):
        variables = {
            "user_id": user_id,
            "include_chaining": False,
            "include_reel": False,
            "include_suggested_users": False,
            "include_logged_out_extras": False,
            "include_highlight_reels": True,
            "include_live_status": True,
        }
        string_vars = json.dumps(variables)
        url = PROFILE_INFO_GRAPH_API.format(variables=string_vars)
        r = self._get_request(url)
        data = r.json()

        highlights_data = {
            edge["node"]["id"]: {
                "title": edge["node"]["title"],
                "id": edge["node"]["id"],
                "reels": [],
                "thumbnail_url": edge["node"]["cover_media"]["thumbnail_src"],
                } for edge in data["data"]["user"]["edge_highlight_reels"]["edges"]
        }
        highlights_ids = [f"highlight:{highlight_id}" for highlight_id in highlights_data.keys()]

        return highlights_data, highlights_ids



    def parse_reel_item(self, item: ReelItemType) -> ParsedItemType:
        item_id = item["pk"]
        owner = item["user"]["pk"]
        owner_user = item["user"].get("username", "")
        timestamp = item.get("taken_at", 0)
        parent_id = item.get("carousel_parent_id") or item.get("parent_id")
        close_friends_only = item.get("audience", "") == "besties"
        has_images = "image_versions2" in item
        has_video = "video_versions" in item
        biggest_photo = max(item["image_versions2"]["candidates"], key=lambda x: x["width"] * x["height"])["url"]
        biggest_video = ""
        if has_video:
            biggest_video = max(item["video_versions"], key=lambda x: x["width"] * x["height"])["url"]
        if not has_images:
            raise Exception(f"Failed to find image {item_id} for reel")
        usertags: Dict[str, List[UserMediaTagType]] = item.get("usertags", {})

        tags: List[ParsedTagUserType] = [
            {
                "id": obj["user"]["pk"],
                "username": obj["user"]["username"]
            }
            for tag_list in usertags.values()
            for obj in tag_list
        ]
        return {
            "id": item_id,
            "owner": owner,
            "owner_username": owner_user,
            "tagged_users": tags,
            "image_url": biggest_photo,
            "video_url": biggest_video,
            "besties_only": close_friends_only,
            "parent": parent_id,
            "time": timestamp,
        }

    def parse_post_item(self, item) -> List[ParsedItemType]:    
        if "carousel_media" not in item:
            return [self.parse_reel_item(item)]
        
        post_items: List[ParsedItemType] = []
        for carousel_item in item["carousel_media"]:
            carousel_item["user"] = item["user"]
            carousel_item["taken_at"] = item["taken_at"]
            post_item = self.parse_reel_item(carousel_item)
            post_items.append(post_item)
        
        return post_items

    def download_list(self, downloads_list: List[ParsedItemType], mappings, folder, download_path):
        default_path = os.path.join(download_path, "{owner}", folder)
        for i, item in enumerate(downloads_list):
            parent_id = item["parent"]
            id_ = item["id"]
            image_name = video_name = f"{parent_id}_{id_}" if parent_id else id_

            try:
                owner = mappings[str(item["owner"])]
            except KeyError:
                print("Possible Repost found", item["owner"])
                # owner = os.path.join("Unknown", str(item["owner"]))
                owner = item["owner_username"] or "Unknown"
            print(f"Downloading item {id_} for {owner} ({i+1}/{len(downloads_list)})", end="\r")

            image = item["image_url"]
            video = item["video_url"]
            besties = item["besties_only"]
            time = item["time"]

            image_ext = get_extension_from_url(image)
            video_ext = get_extension_from_url(video)

            image_path, video_path = self._get_media_out_paths(default_path, besties, video, owner, False)
            os.makedirs(image_path, exist_ok=True)

            if video:
                os.makedirs(video_path, exist_ok=True)
                image_name = image_name + "_thumbnail"
                video_file = os.path.join(video_path, f"{video_name}.{video_ext}")
                download_item(video, video_file, time)

            image_file = os.path.join(image_path, f"{image_name}.{image_ext}")
            download_item(image, image_file, time)

            tagged_users = item["tagged_users"]
            if tagged_users:
                print("Handling Tags in item")
                for user_obj in tagged_users:
                    if not self._is_user_tracked(user_obj["id"], user_obj["username"], mappings, download_path):
                        continue
                    tag_user = user_obj["username"] or mappings.get(str(user_obj["id"]))
                    im_copy, vd_copy = self._get_media_out_paths(default_path, besties, video, tag_user, True)
                    os.makedirs(im_copy, exist_ok=True)
                    self._copy_item(image_file, os.path.join(im_copy, f"{image_name}.{image_ext}"), time)
                    if video:
                        os.makedirs(vd_copy, exist_ok=True)
                        self._copy_item(video_file, os.path.join(vd_copy, f"{video_name}.{video_ext}"), time) # type: ignore
                    
        print()

    def _copy_item(self, from_, to_, time):
        if os.path.exists(to_):
            return False
        shutil.copy2(from_, to_) # type: ignore
        if time > 0:
            set_creation_time(to_, time)
        return True

    def _is_user_tracked(self, user_id: str, user_name: str, mappings: dict, media_path: str):
        if str(user_id) in mappings:
            return True

        if not user_name or user_name == "Unknown":
            return False
        
        if os.path.exists(os.path.join(media_path, user_name, "meta")): # Needs to have meta
            return True
        return False
        

    def _get_media_out_paths(self, default_path: str, is_private: bool, has_video: Optional[str], owner: str, is_tag: bool):
        path = default_path
        if is_tag:
            path = os.path.join(path, "tagged")
        if is_private:
            path = os.path.join(path, "private")
        if has_video:
            image_path = os.path.join(path, "video_thumbnails")
            video_path = path
        else:
            image_path = path
            video_path = ""

        return [s.format(owner=owner) for s in [image_path, video_path]]



            
