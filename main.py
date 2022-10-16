import json
import os
import sys
from math import ceil

from src.api import InstagramDownloader

   
from src.parsers import *
from src.consts import *
from src.utils import *
        

if __name__ == "__main__":

    disable_proxy("instagram.com")

    SESSION_USER = sys.argv[1] if len(sys.argv) > 1 else "TEST"

    try:
        with open("data/list.json", "r") as f:
            usernames_list = json.load(f)
    except Exception:
        print("Failed to load data/list.json")
        exit(1)

    usernames = usernames_list[SESSION_USER].get("users", [])
    sessionid = usernames_list[SESSION_USER].get("sessionid", None)
    if sessionid is None:
        raise Exception("Invalid Session ID provided")

    instagram = InstagramDownloader(sessionid)

    for username in usernames:
        os.makedirs(os.path.join(MEDIA_PATH, username, "meta"), exist_ok=True)

    username_mappings = {}
    all_usernames = {}
    usernames_path = os.path.join(MEDIA_PATH, "usernames.json")
    if os.path.exists(usernames_path):
        with open(usernames_path, "r", encoding="utf-8") as f:
            all_usernames = json.load(f)
            for u_id, u_name in all_usernames.items():
                if u_name in usernames:
                    username_mappings[u_id] = u_name        

    for username in usernames:
        # Add something to refresh profile pic if pic isn't today
        if username in username_mappings.values():
            continue
        print("Getting user id of", username)
        user = instagram.get_user_profile(username)
        user_id = user["id"]
        profile_pic = user.get("profile_pic_url_hd") or user["profile_pic_url"]
        username_mappings[user_id] = username
        all_usernames[user_id] = username

        pro_pic_path = os.path.join(MEDIA_PATH, username, "profile_pics")
        os.makedirs(pro_pic_path, exist_ok=True)
        pro_pic_path = os.path.join(pro_pic_path, get_time_now_as_hour() + "." + get_extension_from_url(profile_pic))
        download_item(profile_pic, pro_pic_path)
    
    with open(usernames_path, "w", encoding="utf-8") as f:
        json.dump(all_usernames, f, indent=4, ensure_ascii=False)

    # Traverse stories 3 at a time
    users = list(username_mappings.keys())
    for i in range(0, len(usernames), 3):
        cur_users = users[i:i+3]
        cur_usernames = [username_mappings[uid] for uid in cur_users]
        print("Getting stories for", " ".join(cur_usernames))

        data = instagram.get_reels_data(cur_users)

        for story_data, user_id in instagram.parse_reels_data(data, username_mappings):
            username = username_mappings[str(user_id)]
            story_path = os.path.join(MEDIA_PATH, username, "meta")
            cur_hour = get_time_now_as_hour()
            story_file = os.path.join(story_path, f"story_{cur_hour}.json")
            
            with open(story_file, "w", encoding='utf-8') as f:
                json.dump(story_data, f, ensure_ascii=False, indent=4)

            download_list(story_data, username_mappings, "stories")

    for user_id, username in username_mappings.items():
        print("Getting posts for", username, user_id)

        posts_folder = os.path.join("posts")
        posts_meta_path = os.path.join(MEDIA_PATH, username, "meta")
        posts_file = os.path.join(posts_meta_path, "posts.json")
        if os.path.exists(posts_file):
            with open(posts_file, encoding='utf-8') as f:
                old_posts = json.load(f)
        else:
            old_posts = []

        posts_data = list(instagram.get_posts_data(user_id, old_posts))
        full_posts = []
        for posts in instagram.parse_posts_data(posts_data):
            full_posts.extend(posts)
        download_list(full_posts, username_mappings, posts_folder)


        with open(posts_file, "w", encoding='utf-8') as f:
            json.dump(full_posts + old_posts, f, ensure_ascii=False, indent=4)

    for user_id, username in username_mappings.items():
        print("Getting highlights for", username, user_id)
        highlights_data, highlights_ids = instagram.get_highlights_data(user_id)
        
        for i in range(0, len(highlights_ids), LIMIT): # Walk 3 at a time
            print(f"Getting page {i//LIMIT +1} / {ceil(len(highlights_ids)/LIMIT)}")
            cur_h = highlights_ids[i:i+LIMIT]
            data = instagram.get_reels_data(cur_h)
            
            for j, highlight in enumerate(data["reels"].values()):
                h_id = highlight["id"].split(":", 1)[-1]
                items = highlight["items"]
                highlights_data[h_id]["reels"].extend(instagram.parse_highlights_data(items))

                highlights_folder = os.path.join("highlights", h_id)
                highlights_folder_full_path = os.path.join(MEDIA_PATH, username, highlights_folder)
                print(f"Getting highlight {h_id} ({j+1}/{LIMIT})")
                download_list(highlights_data[h_id]["reels"], username_mappings, highlights_folder)

                print("Saving name and thumbnail")
                thumb_url = highlights_data[h_id]["thumbnail_url"]
                thumb_path = os.path.join(highlights_folder_full_path, "thumbnail." + get_extension_from_url(thumb_url))
                download_item(thumb_url, thumb_path)
                print()
                with open(os.path.join(highlights_folder_full_path, "name.txt"), "w", encoding="utf-8") as f:
                    f.write(highlights_data[h_id]["title"])
                            

        highlights_path = os.path.join(MEDIA_PATH, username, "meta")
        os.makedirs(highlights_path, exist_ok=True)

        highlights_file = os.path.join(highlights_path, "highlights.json")
        with open(highlights_file, "w", encoding='utf-8') as f:
            json.dump(highlights_data, f, ensure_ascii=False, indent=4)
