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
    download_profile_pic,
    get_extension_from_url,
    get_time_now_as_hour,
    get_time_now_as_week,
    unquote_sid,
    verify_profile_pic,
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
        help=f"The number of calls to do per one call. Keep it at a low number to avoid huge payload, but not too low to avoid rate limiting. (Default {LIMIT})",
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
        "--disable-save-reels",
        "--no-reels",
        "-r",
        dest="dl_reels",
        action="store_true", # Until I find a workaround this is store_true
        help="Disable downloading Reels if on",
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
        help="Download Stories only",
    )
    save_only_group.add_argument(
        "--save-posts-only",
        "--only-posts",
        "-P",
        dest="posts_only",
        action="store_true",
        help="Download Posts only",
    )
    save_only_group.add_argument(
        "--save-reels-only",
        "--only-reels",
        "-R",
        dest="reels_only",
        action="store_true",
        help="Download Reels only",
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
    options_group.add_argument(
        "--no-profile-pics",
        "-n",
        dest="profile_pic_download",
        help="Disable downloading profile pics",
        action="store_false",
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
    dl_reels: bool = args.dl_reels
    dl_high: bool = args.dl_high

    bypass_proxy: bool = args.bypass_proxy
    sleep_duration: int = args.sleep_duration
    profile_pic_download: bool = args.profile_pic_download

    if args.story_only:
        dl_story = args.dl_story = True
        dl_posts = args.dl_posts = False
        dl_reels = args.dl_reels = False
        dl_high = args.dl_high = False
    elif args.posts_only:
        dl_story = args.dl_story = False
        dl_posts = args.dl_posts = True
        dl_reels = args.dl_reels = False
        dl_high = args.dl_high = False
    elif args.reels_only:
        dl_story = args.dl_story = False
        dl_posts = args.dl_posts = False
        dl_reels = args.dl_reels = True
        dl_high = args.dl_high = False
    elif args.high_only:
        dl_story = args.dl_story = False
        dl_posts = args.dl_posts = False
        dl_reels = args.dl_reels = False
        dl_high = args.dl_high = True

    if dl_reels:
        print("Reels downloading is disable since it's triggering instagram bot detection")
        exit(2)
    dl_reels = False # Turn it off since it's causing issues with csrftoken logging out instagram

    if bypass_proxy:
        disable_proxy("instagram.com")

    usernames_list: Dict[str, ListUserType]

    def load_users_file(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                listobject: ListObjectType = json.load(f)
                usernames_list = listobject.get("categories")
                session_map = listobject.get("sessionids")
        except Exception:
            raise Exception(f"Failed to load list json: {file_path}")
        return usernames_list, session_map

    if passed_session_id or passed_users:
        if all_users:
            raise ValueError("When Users are passed, All Users flag cannot be used.")
        if not passed_session_id or not passed_users:
            raise ValueError("Session Id and Users must be passed together.")
        try:
            usernames_list, session_map = load_users_file(input_file)
            found_session_id = session_map.get(passed_session_id)
            if found_session_id is not None:
                print("Session Id treated as Key")
                passed_session_id = found_session_id
        except Exception:
            pass

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
        usernames_list, session_map = load_users_file(input_file)
        if all_users:
            args.users = session_users = list(usernames_list.keys())

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
            os.makedirs(os.path.join(downloads_folder, username, "profile_pics"), exist_ok=True)

        username_mappings = {}
        all_usernames = {}
        users_found = set()
        usernames_path = os.path.join(downloads_folder, "usernames.json")
        if os.path.exists(usernames_path):
            with open(usernames_path, "r", encoding="utf-8") as f:
                all_usernames = json.load(f)
                for u_id, u_name in all_usernames.items():
                    if u_name in usernames:
                        username_mappings[u_id] = u_name
                        users_found.add(u_name)

        time_str = get_time_now_as_week()
        missing_profile_pic_ids = {}

        us_rm = set()
        for username in usernames:
            if username not in users_found:
                print(f"New user {username} detected!")
                user = instagram.get_user_profile(username)
                if user is None:
                    print(f"User {username} does not existed or was deleted!")
                    us_rm.add(username)
                    continue
                profile_pic = user.get("profile_pic_url_hd") or user.get("profile_pic_url") or sd_url
                user_id = user.get("id")
                username_mappings[user_id] = username
                all_usernames[user_id] = username
                download_profile_pic(profile_pic, username, downloads_folder, time_str)

        if us_rm:
            print(f"Removing a total of {len(us_rm)} deleted users!")
        for user in us_rm:
            usernames.remove(user)

        with open(usernames_path, "w", encoding="utf-8") as f:
            json.dump(all_usernames, f, indent=4, ensure_ascii=False)

        # Traverse stories LIMIT*3 at a time
        users = list(username_mappings.keys())
        for i in range(0, len(usernames) if dl_story else 0, download_limit*3):
            sleep(sleep_duration)
            cur_users = users[i : i + download_limit*3]
            cur_usernames = [username_mappings[uid] for uid in cur_users]
            print("Getting stories for", " ".join(cur_usernames))

            data = instagram.get_story_reels_data(cur_users)
            missing_profile_pic_ids.update(
                verify_profile_pic(
                    data["reels"].values(),
                    downloads_folder,
                    missing_profile_pic_ids
                )
            )

            for story_data, user_id in instagram.parse_story_reels_data(
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
            missing_profile_pic_ids.update(verify_profile_pic(posts_data, downloads_folder, missing_profile_pic_ids, force=True)) # Force redownload all pics, it won't take much and it's just one time, and better safe than sorry, since this is already HD.
            full_posts = []
            for posts in instagram.parse_posts_data(posts_data):
                full_posts.extend(posts)
            instagram.download_list(
                full_posts, username_mappings, posts_folder, downloads_folder
            )

            with open(posts_file, "w", encoding="utf-8") as f:
                json.dump(full_posts + old_posts, f, ensure_ascii=False, indent=4)

        for user_id, username in username_mappings.items() if dl_reels else []:
            sleep(sleep_duration)
            print("Getting reels for", username, user_id)

            reels_folder = os.path.join("reels")
            reels_meta_path = os.path.join(downloads_folder, username, "meta")
            reels_file = os.path.join(reels_meta_path, "reels.json")
            if os.path.exists(reels_file):
                with open(reels_file, encoding="utf-8") as f:
                    old_reels = json.load(f)
            else:
                old_reels = []

            reels_data = list(instagram.get_reels_data(user_id, old_reels))
            full_reels = []
            for reels in instagram.parse_posts_data(reels_data):
                full_reels.extend(reels)
            instagram.download_list(
                full_reels, username_mappings, reels_folder, downloads_folder
            )

            with open(reels_file, "w", encoding="utf-8") as f:
                json.dump(full_reels + old_reels, f, ensure_ascii=False, indent=4)

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
                data = instagram.get_story_reels_data(cur_h)

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
                    download_item(thumb_url, thumb_path, desc="thumbnail")
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

        # Download profile pictures
        if not profile_pic_download:
            continue

        print("Validating profile pictures")
        for username in usernames:
            if username in missing_profile_pic_ids:
                continue
            pro_pic_path = os.path.join(downloads_folder, username, "profile_pics")
            pro_pic_file_path = os.path.join(pro_pic_path, "last.txt")
            os.makedirs(pro_pic_path, exist_ok=True)
            if username in username_mappings.values():
                if os.path.exists(pro_pic_file_path):
                    with open(pro_pic_file_path) as f:
                        last_date = f.read().strip()
                        if last_date == time_str:
                            continue
                print(f"Profile pic expired for {username}, getting a new one.")
                missing_profile_pic_ids[username] = {}

        for username, user_obj in missing_profile_pic_ids.items():
            print(f"Profile pic for {username} expired. Getting a new one!")
            sleep(sleep_duration)
            user_id = user_obj.get("id")
            sd_url = user_obj.get("sd_url")
            hd_url = user_obj.get("hd_url")
            hd_max_url = user_obj.get("hd_max_url")
            force = False
            if hd_max_url:
                profile_pic = hd_max_url
                force = True
            elif hd_url:
                profile_pic = hd_url
            else:
                user = instagram.get_user_profile(username)
                profile_pic = user.get("profile_pic_url_hd") or user.get("profile_pic_url") or sd_url
                user_id = user.get("id")
            username_mappings[user_id] = username
            all_usernames[user_id] = username
            download_profile_pic(profile_pic, username, downloads_folder, time_str, force=force)
