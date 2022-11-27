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
        os.utime(file, times=(time,)*2)

def download_item(url: str, store_path: str, timestamp: int = 0, retry_count: int = 0):
    if retry_count > 3:
        print("Retry Count Exceeded for", url)
        return False
    if os.path.exists(store_path):
        print("Already exists", store_path, end="\r")
        return False

    with requests.get(url, stream=True) as context:
        if context.status_code == 410:
            print("Cannot download", url, "for error 410")
            return False
        if context.status_code // 100 == 5:
            print("Server error on", url, context.status_code)
            return download_item(url, store_path, timestamp, retry_count+1)
        
        context.raise_for_status()
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
