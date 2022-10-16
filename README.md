# INSTAGRAM DOWNLOADER
Lets say you found a meme page that you loved so much

Lets say you want to download all the memes

Good, now all you have to do is put your session id in [data/list.json](data/list.json) as well as the meme page name and run [main](main.py)

```py
python main.py
```

Now sit and wait for all the meme and glory. But if you're in the EU then you didn't download this tool from me 🤷🏻‍♂️

If you want to have multiple categories then you can use them as an `arg` to `main` such as 
```py
python main.py communist_memes
```
And you can categorize the meme pages by their type of memes.

## How to get your session id

### Sign in to instagram 
1. on PC
2. or mobile browser with chrome dev-tools (adb)
3. or mobile phone with charles certificate installed
4. or nox emulator Android 5 with charles certificate installed
5. or bluestacks 3 with proxycap and bluestacks proxy passed through charles

### Methods 1-2
1. Open the browser Developer Options using F12 or right click > inspect.
   - Using Cookies:
      1. Go to Application
      2. Click on Cookies
      3. Select instagram
   - Using Network:
      1. Go to Network
      2. Open any profile page
      3. Select any GET request
      4. Go to Request Headers
      5. copy the Cookie
      6. extract `sessionid` from the cookie until the `;` 
2. Copy the `sessionid`'s value


### Methods 3-5
1. Open Charles Proxy
2. Enable SSL Proxying
3. Install the certificate on your device (for mobile, I won't help you cuz it's too much trouble)
4. Follow the previous method's 1>Network>2
5. Copy the `sessionid`'s value


### After you have the `sessionid` put it in the file and run

