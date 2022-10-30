import json
import os
from argparse import ArgumentParser
from math import ceil
from time import sleep
from typing import Dict, List

from src.api import InstagramDownloader
from src.consts import LIMIT, MEDIA_PATH
from src.utils import (
    disable_proxy,
    download_item,
    get_extension_from_url,
    get_file_name_from_url,
    get_time_now_as_day,
    get_time_now_as_hour,
    unquote_sid,
)
from src.validators import ListObjectType, ListUserType


def parse_args(*args):
    parser = ArgumentParser("InstagramDownloader")
    parser.add_argument(
        "users",
        metavar="categories",
        type=str,
        nargs="*",
        help="The categories that has the sessionid and the users to scrape",
        default=["TEST"],
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="download_path",
        type=str,
        help="The folder to store downloaded files in.",
        default=MEDIA_PATH,
    )
    parser.add_argument(
        "--download-limit",
        "-l",
        dest="download_limit",
        type=int,
        help="The number of calls to do per one call. Keep it at a low number to avoid huge payload, but not too low to avoid rate limiting. (Default 3)",
        default=LIMIT,
    )

    input_group = parser.add_argument_group(title="Input Methods")
    input_group.add_argument(
        "--input-file",
        "-f",
        type=str,
        help="The json file to load session and users from",
        default=os.path.join("data", "list.json"),
    )
    input_group.add_argument(
        "--all-categories",
        "-a",
        dest="all_users",
        action="store_true",
        help="Automatically goes through all the categories",
    )
    input_group.add_argument(
        "--session-id", "-e", type=str, help="Your session id to login as.", default=""
    )
    input_group.add_argument(
        "--users",
        "-u",
        metavar="USERNAME",
        dest="usernames",
        type=str,
        nargs="+",
        help="The usernames to download",
        default=[],
    )

    save_group = parser.add_argument_group(title="Download Switches")
    save_group.add_argument(
        "--disable-save-story",
        "--no-story",
        "-s",
        dest="dl_story",
        action="store_false",
        help="Disable downloading Stories if on",
    )
    save_group.add_argument(
        "--disable-save-posts",
        "--no-posts",
        "-p",
        dest="dl_posts",
        action="store_false",
        help="Disable downloading Posts if on",
    )
    save_group.add_argument(
        "--disable-save-highlights",
        "--no-highlights",
        "-i",
        dest="dl_high",
        action="store_false",
        help="Disable downloading Highlights if on",
    )

    save_only_group = save_group.add_mutually_exclusive_group()
    save_only_group.add_argument(
        "--save-story-only",
        "--only-story",
        "-S",
        dest="story_only",
        action="store_true",
        help="Download stories only",
    )
    save_only_group.add_argument(
        "--save-posts-only",
        "--only-posts",
        "-P",
        dest="posts_only",
        action="store_true",
        help="Download posts only",
    )
    save_only_group.add_argument(
        "--save-highlights-only",
        "--only-highlights",
        "-I",
        dest="high_only",
        action="store_true",
        help="Download Highlights only",
    )

    options_group = parser.add_argument_group("Options")
    options_group.add_argument(
        "--allow-proxy",
        "-x",
        dest="bypass_proxy",
        action="store_false",
        help="Allow usage of os proxy. If off (default) then python will bypass proxy.",
    )
    options_group.add_argument(
        "--sleep-time",
        "-t",
        dest="sleep_duration",
        help="Time to wait in between requests in seconds",
        metavar="SECONDS",
        default=1,
    )

    if args:
        return parser.parse_args(args)
    else:
        return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()

    session_users: List[str] = args.users
    downloads_folder: str = args.download_path
    download_limit: int = args.download_limit

    input_file: str = args.input_file
    passed_session_id: str = args.session_id
    passed_users: List[str] = args.usernames
    all_users: bool = args.all_users

    dl_story: bool = args.dl_story
    dl_posts: bool = args.dl_posts
    dl_high: bool = args.dl_high

    bypass_proxy: bool = args.bypass_proxy
    sleep_duration: int = args.sleep_duration

    if args.story_only:
        dl_story = args.dl_story = True
        dl_posts = args.dl_posts = False
        dl_high = args.dl_high = False
    elif args.posts_only:
        dl_story = args.dl_story = False
        dl_posts = args.dl_posts = True
        dl_high = args.dl_high = False
    elif args.high_only:
        dl_story = args.dl_story = False
        dl_posts = args.dl_posts = False
        dl_high = args.dl_high = True

    if bypass_proxy:
        disable_proxy("instagram.com")

    usernames_list: Dict[str, ListUserType]

    if passed_session_id or passed_users:
        if all_users:
            raise ValueError(
                "When Input File is not specified, All Users flag cannot be used."
            )
        if not passed_session_id or not passed_users:
            raise ValueError(
                "When Input File is not specified, both session id and users must be passed."
            )
        session_map = {
            "S": passed_session_id,
        }
        usernames_list = {
            "passed": {
                "sessionid": "S",
                "users": passed_users,
            }
        }
        args.users = session_users = ["passed"]
    else:
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                listobject: ListObjectType = json.load(f)
                usernames_list = listobject.get("categories")
                session_map = listobject.get("sessionids")
                if all_users:
                    args.users = session_users = list(usernames_list.keys())
        except Exception:
            raise Exception("Failed to load data/list.json")

    for session_user in session_users:

        usernames = usernames_list[session_user].get("users", [])

        sessionid_tag = usernames_list[session_user].get("sessionid", None)
        if sessionid_tag is None:
            raise Exception("Invalid Session ID Reference provided")

        sessionid = session_map.get(sessionid_tag, None)
        if sessionid is None:
            raise Exception("Invalid Session ID provided")
        sessionid = unquote_sid(sessionid)

        instagram = InstagramDownloader(sessionid)

        for username in usernames:
            os.makedirs(os.path.join(downloads_folder, username, "meta"), exist_ok=True)

        username_mappings = {}
        all_usernames = {}
        usernames_path = os.path.join(downloads_folder, "usernames.json")
        if os.path.exists(usernames_path):
            with open(usernames_path, "r", encoding="utf-8") as f:
                all_usernames = json.load(f)
                for u_id, u_name in all_usernames.items():
                    if u_name in usernames:
                        username_mappings[u_id] = u_name

        for username in usernames:
            # Add something to refresh profile pic if pic isn't today
            pro_pic_path = os.path.join(downloads_folder, username, "profile_pics")
            pro_pic_file_path = os.path.join(pro_pic_path, "last.txt")
            os.makedirs(pro_pic_path, exist_ok=True)
            if username in username_mappings.values():
                time_str = get_time_now_as_day()
                if os.path.exists(pro_pic_file_path):
                    with open(pro_pic_file_path) as f:
                        last_date = f.read().strip()
                        if last_date == time_str:
                            continue
                print("Profile pic expired, getting a new one.")
            sleep(sleep_duration) # Sleep after checking local and not before
            print("Getting user id of", username)
            user = instagram.get_user_profile(username)
            user_id = user["id"]
            profile_pic = user.get("profile_pic_url_hd") or user["profile_pic_url"]
            username_mappings[user_id] = username
            all_usernames[user_id] = username

            pro_pic_file = get_file_name_from_url(profile_pic)
            pro_pic_path = os.path.join(
                pro_pic_path,
                pro_pic_file,
            )
            download_item(profile_pic, pro_pic_path)
            with open(pro_pic_file_path, "w") as f:
                f.write(get_time_now_as_day())

        with open(usernames_path, "w", encoding="utf-8") as f:
            json.dump(all_usernames, f, indent=4, ensure_ascii=False)

        # Traverse stories 3 at a time
        users = list(username_mappings.keys())
        for i in range(0, len(usernames) if dl_story else 0, download_limit):
            sleep(sleep_duration)
            cur_users = users[i : i + download_limit]
            cur_usernames = [username_mappings[uid] for uid in cur_users]
            print("Getting stories for", " ".join(cur_usernames))

            data = instagram.get_reels_data(cur_users)

            for story_data, user_id in instagram.parse_reels_data(
                data, username_mappings
            ):
                username = username_mappings[str(user_id)]
                story_path = os.path.join(downloads_folder, username, "meta")
                cur_hour = get_time_now_as_hour()
                story_file = os.path.join(story_path, f"story_{cur_hour}.json")

                with open(story_file, "w", encoding="utf-8") as f:
                    json.dump(story_data, f, ensure_ascii=False, indent=4)

                instagram.download_list(
                    story_data, username_mappings, "stories", downloads_folder
                )

        for user_id, username in username_mappings.items() if dl_posts else []:
            sleep(sleep_duration)
            print("Getting posts for", username, user_id)

            posts_folder = os.path.join("posts")
            posts_meta_path = os.path.join(downloads_folder, username, "meta")
            posts_file = os.path.join(posts_meta_path, "posts.json")
            if os.path.exists(posts_file):
                with open(posts_file, encoding="utf-8") as f:
                    old_posts = json.load(f)
            else:
                old_posts = []

            posts_data = list(instagram.get_posts_data(user_id, old_posts))
            full_posts = []
            for posts in instagram.parse_posts_data(posts_data):
                full_posts.extend(posts)
            instagram.download_list(
                full_posts, username_mappings, posts_folder, downloads_folder
            )

            with open(posts_file, "w", encoding="utf-8") as f:
                json.dump(full_posts + old_posts, f, ensure_ascii=False, indent=4)

        for user_id, username in username_mappings.items() if dl_high else []:
            sleep(sleep_duration)
            print("Getting highlights for", username, user_id)
            highlights_data, highlights_ids = instagram.get_highlights_data(user_id)

            for i in range(0, len(highlights_ids), download_limit):  # Walk 3 at a time
                sleep(sleep_duration)
                print(
                    f"Getting page {i//download_limit +1} / {ceil(len(highlights_ids)/download_limit)}"
                )
                cur_h = highlights_ids[i : i + download_limit]
                data = instagram.get_reels_data(cur_h)

                for j, highlight in enumerate(data["reels"].values()):
                    h_id = highlight["id"].split(":", 1)[-1]
                    items = highlight["items"]
                    highlights_data[h_id]["reels"].extend(
                        instagram.parse_highlights_data(items)
                    )

                    highlights_folder = os.path.join("highlights", h_id)
                    highlights_folder_full_path = os.path.join(
                        downloads_folder, username, highlights_folder
                    )
                    print(f"Getting highlight {h_id} ({j+1}/{download_limit})")
                    instagram.download_list(
                        highlights_data[h_id]["reels"],
                        username_mappings,
                        highlights_folder,
                        downloads_folder,
                    )

                    print("Saving name and thumbnail")
                    thumb_url = highlights_data[h_id]["thumbnail_url"]
                    thumb_path = os.path.join(
                        highlights_folder_full_path,
                        "thumbnail." + get_extension_from_url(thumb_url),
                    )
                    download_item(thumb_url, thumb_path)
                    print()
                    with open(
                        os.path.join(highlights_folder_full_path, "name.txt"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(highlights_data[h_id]["title"])

            highlights_path = os.path.join(downloads_folder, username, "meta")
            os.makedirs(highlights_path, exist_ok=True)

            highlights_file = os.path.join(highlights_path, "highlights.json")
            with open(highlights_file, "w", encoding="utf-8") as f:
                json.dump(highlights_data, f, ensure_ascii=False, indent=4)
