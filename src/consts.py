from src.utils import url_join

IG_APP_ID = "936619743392459"
IG_HEADERS = {
    "x-ig-app-id": IG_APP_ID
}
PROFILE_QUERY_HASH = "d4d88dc1500312af6f937f7b804c68c3"

INSTAGRAM_API_V1 = "https://i.instagram.com/api/v1/"
INSTAGRAM_API_GRAPH = "https://instagram.com/graphql/"
INSTAGRAM_API_BASIC = ""

# V1
STORY_API = url_join(INSTAGRAM_API_V1, "feed/reels_media/?reel_ids={ids_string}")
USER_ID_API = url_join(INSTAGRAM_API_V1, "users/web_profile_info/?username={username}")
STORY_HIGHLIGHTS_API = url_join(INSTAGRAM_API_V1, "highlights/{user_id}/highlights_tray")
FEED_API = url_join(INSTAGRAM_API_V1, "feed/user/{user_id}/?count={count}&max_id={last_post_id}")
# Graph
PROFILE_INFO_GRAPH_API = url_join(INSTAGRAM_API_GRAPH, "query", f"?query_hash={PROFILE_QUERY_HASH}&variables=""{variables}")

MEDIA_PATH = "media"
LIMIT = 3