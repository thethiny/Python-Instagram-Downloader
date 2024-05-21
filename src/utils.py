import os
import re
import shutil
from datetime import datetime
from urllib.parse import unquote_plus

try:
    import filedate
except ModuleNotFoundError:
    filedate = None


import requests

PROTOCOL_RE = re.compile(r"^(https?)://")
def url_join(*urls: str, domain=""):
    if not urls:
        return ""
    if urls[0].startswith("/") and not domain: # Do not allow absolutes with no domain
        raise ValueError("Cannot append url with no known domain")

    string = ""
    protocol = ""
    first = True
    for url in urls:
        url = url.strip()
        if not url:
            continue
        if first:
            protocol_re = PROTOCOL_RE.search(url)
            if protocol_re:
                protocol = protocol_re.group(1)
                url = url.split("://", 1)[1]
            domain = url.split("/", 1)[0]
            first = False
        if url and url[0] == "/": # root
            string = domain
            url = url.lstrip("/")
        if string and string[-1] == "/":
            string += url
        else:
            string += ("/" if string else "") + url

    return f"{protocol}://{string}"

def get_extension_from_url(url):
    return url.split("?", 1)[0].rsplit(".", 1)[-1]

def get_file_name_from_url(url):
    return url.strip("/").split("?", 1)[0].rsplit("/", 1)[-1]

def timestamp_to_iso(timestamp: int):
    time = datetime.fromtimestamp(timestamp)
    time = time.isoformat()
    return time

def set_creation_time(file, time: int):
    if filedate:
        ts = timestamp_to_iso(time)
        filedate.File(file).set(
            created=ts,
            modified=ts,
            accessed=ts,
        )
    else:
        os.utime(file, times=(time,)*2) # type: ignore

def download_item(url: str, store_path: str, timestamp: int = 0, retry_count: int = 0, force: bool = False):
    if retry_count > 3:
        print("Retry Count Exceeded for", url)
        return False
    if os.path.exists(store_path) and not force:
        print("Already exists", store_path, end="\r")
        return False

    with requests.get(url, stream=True) as context:
        if context.status_code == 410:
            print("Cannot download", url, "for error 410")
            return False
        if context.status_code // 100 == 5:
            print("Server error on", url, context.status_code)
            return download_item(url, store_path, timestamp, retry_count+1)
        if context.status_code == 404:
            print("Item deleted", url)
            return False
        
        context.raise_for_status()
        if store_path == "memory":
            return context.raw
        with open(store_path, "wb") as f:
            shutil.copyfileobj(context.raw, f)
        if timestamp > 0:
            set_creation_time(store_path, timestamp)
    
    return True

def disable_proxy(*domain):
    if not domain or (domain and not domain[0]):
        os.environ["NO_PROXY"] = "*"
        return
    domain = ','.join(domain)
    os.environ["NO_PROXY"] = ",".join([os.environ.get("NO_PROXY",""), domain]).strip(",")
    return

def get_time_now():
    return datetime.utcnow()

def get_time_now_as_hour():
    return get_time_now().strftime(r"%d-%m-%y_%H")

def get_time_now_as_day():
    return get_time_now().strftime(r"%d-%m-%y")

def get_time_now_as_week():
    return get_time_now().strftime(r"%W")

def unquote_sid(sid):
    if "%" in sid:
        return unquote_plus(sid)
    return sid

def check_profile_pic_exists(pic_url, username, downloads_folder):
    if not pic_url:
        return None
    pro_pic_name = get_file_name_from_url(pic_url)
    pic_path = os.path.join(downloads_folder, username, "profile_pics", pro_pic_name)
    return os.path.isfile(pic_path)
    

def verify_profile_pic(contains_user_iter, downloads_folder, current_missing_pics, force: bool = False, force_mode="hd"): # force mode will only force if it's HD
    current_pics = {}
    for item in contains_user_iter:
        pic_user = item.get("user")
        user_pic_hd_max = pic_user.get("hd_profile_pic_url_info", {}).get("url")
        user_pic_hd = pic_user.get("profile_pic_url_hd")
        user_pic_sd = pic_user.get("profile_pic_url")
        user_obj = {
            "id": pic_user.get("id"),
            "sd_url": user_pic_sd,
            "hd_url": user_pic_hd,
            "hd_max_url": user_pic_hd_max,
        }
        user_username = pic_user.get("username")
        if not user_username:
            continue
        if current_missing_pics.get(user_username, {}).get("hd_max_url"):
            user_obj["hd_max_url"] = current_missing_pics.get(user_username, {}).get("hd_max_url")
        if current_missing_pics.get(user_username, {}).get("hd_url"):
            user_obj["hd_url"] = current_missing_pics.get(user_username, {}).get("hd_url")
        if force:
            if force_mode == "hd":
                if user_pic_hd_max:
                    current_pics[user_username] = user_obj
                    continue
            else:
                current_pics[user_username] = user_obj
        if check_profile_pic_exists(user_pic_hd_max or user_pic_hd or user_pic_sd, user_username, downloads_folder): # All profile picture urls give the same name
            continue

        current_pics[user_username] = user_obj
    return current_pics
        
def download_profile_pic(pic_url, pic_user, downloads_folder, time_str, force: bool = False):
    pro_pic_file = get_file_name_from_url(pic_url)
    pro_pic_path = os.path.join(downloads_folder, pic_user, "profile_pics")
    pro_pic_file_path = os.path.join(pro_pic_path, pro_pic_file)
    dl_ret = download_item(pic_url, pro_pic_file_path, force=force)
    pro_pic_file_path = os.path.join(pro_pic_path, "last.txt")
    with open(pro_pic_file_path, "w") as f:
        f.write(time_str)
    return dl_ret
    
