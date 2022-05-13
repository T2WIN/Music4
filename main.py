from selenium import webdriver
import time
from pytube import YouTube
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException
import sqlite3


class SongDownload:

    def __init__(self, path, db):
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.path = path
        self.current_song = None
        self.bot_protect = True
        self.db = db

    def find_song(self, search_string):
        def adapt_title(title):
            if "Kylie" in title:
                print(title)
                print(" – " in title)
                print(title.split(" - "))
            if " - " in title:
                title2 = title.split(" - ")[1].split("\n")[0]
                artist = title.split(" - ")[0].split("\n")[1]
            elif " – " in title: #Apparently there are multiple types of " - "
                title2 = title.split(" – ")[1].split("\n")[0]
                artist = title.split(" – ")[0].split("\n")[1]
            else:
                title2 = title.split(" - ")[1].split("\n")[0]
                artist = title.split(" - ")[0].split("\n")[1]
            print(title2)
            return [title2, artist]

        start_time = time.time()
        search_text = [x for x in search_string.split(" ")]
        url = "https://www.youtube.com/results?search_query="
        for x in search_text:
            url += "+" + x
        self.driver.get(url)
        time.sleep(0.5)
        if self.bot_protect:
            button = self.driver.find_elements(By.CLASS_NAME, "style-scope.ytd-button-renderer.style-primary.size-default")
            button[2].click()
            self.bot_protect = False
            time.sleep(4)
        song_url = self.driver.find_element(By.ID, "video-title").get_attribute("href")
        song_title = self.driver.find_element(By.CLASS_NAME, "style-scope.ytd-video-renderer").text
        # current_song : list with 3 elements, Title/Artist/URL
        self.current_song = adapt_title(song_title) + [song_url]
        # print(self.current_song)
        return self.current_song

    def download(self):
        yt = YouTube(self.current_song[-1])
        stream = yt.streams[-3]
        stream.download(self.path)
        self.db.add_song(self.current_song)

    def search_artist(self, name):
        start_time = time.time()
        a = name.split(" ")
        # print(name)
        if len(a) == 2:
            url = f"https://www.google.com/search?q=all+{a[0]}+{a[1]}+songs"
        elif len(a) == 1:
            url = f"https://www.google.com/search?q=all+{a[0]}+songs"
        self.driver.get(url)
        if self.bot_protect:
            button = self.driver.find_elements(By.CLASS_NAME, "tHlp8d")
            button[3].click()
            self.bot_protect = False
        songs = [x.text for x in self.driver.find_elements(By.CLASS_NAME, "bVj5Zb.FozYP")]

        next_page = self.driver.find_element(By.CLASS_NAME, "PUDfGe.S3PB2d.z1asCe.kKuqUd")

        while next_page:
            try:
                next_page.click()
                time.sleep(0.5)
                for x in self.driver.find_elements(By.CLASS_NAME, "bVj5Zb.FozYP"):
                    if x.text not in songs:
                        songs.append(x.text)
                next_page = self.driver.find_element(By.CLASS_NAME, "PUDfGe.S3PB2d.z1asCe.kKuqUd")
            except ElementNotInteractableException:
                break
        print(f"Time : {time.time() - start_time}")
        return songs

    def download_artist(self, name):
        start_time = time.time()
        liste = self.search_artist(name)
        print(liste)
        for z in liste:
            # You have to find the song to have it as current song to download it
            self.find_song(name + " " + z)
            self.download()
        print(f"Total Time : {time.time() - start_time}")


class Database:

    def __init__(self, file):
        self.conn = None
        self.create_db_connection(file)

    def create_db_connection(self, file):
        try:
            self.conn = sqlite3.connect(file)
        except:
            print("Error connecting to database")

    def add_song(self, info):

        def rearrange(title):
            a = title
            separators = [x for x in [" & ", " ft ", " x ", "ft.", ", "] if a.find(x) !=-1]
            # print(separators)
            names = []
            for i, x in enumerate(separators):
                # print(x, i)
                if i == 0:
                    names.append(a[:a.find(x)])
                    previous_id = a.find(x) + len(x)
                    if len(separators) == 1:
                        names.append(a[a.find(x) + len(x):])
                elif i == len(separators)-1:
                    names.append(a[previous_id:a.find(x)])
                    names.append(a[a.find(x) + len(x):])
                else:
                    names.append(a[previous_id: a.find(x)])
                    previous_id = a.find(x) + len(x)
            # print(names)
            if not separators:
                names = [title]
            return names

        def find_related_artists(title_data):
            ar_ids = []
            names = rearrange(title_data)
            for name in names:
                id = cur.execute(f'SELECT ar_id FROM artists WHERE ar_name = "{name}" ')
                id = [x for x in id]
                # print(name)
                # If artist already in database return ar_id else add artist to database and then return ar_id
                if id:
                    print("yes")
                    ar_ids.append(str(id[0][0]))
                else:
                    print("no")
                    self.add_artist(name)
                    id = cur.execute(f'SELECT ar_id FROM artists WHERE ar_name = "{name}" ')
                    id = [x for x in id]
                    # print(id, name)
                    ar_ids.append(str(id[0][0]))

            artists = ",".join(ar_ids)
            # print(artists)
            return artists

        cur = self.conn.cursor()
        if not self.check_duplicate_songs(info[0]):
            artists = find_related_artists(info[1])
            # print(info[1])
            id = len([x for x in cur.execute("SELECT song_id FROM songs")]) + 1
            cur.execute('INSERT INTO songs values (?,?,?,?)', (id, info[0], info[-1], artists))
        self.conn.commit()

    def add_artist(self, name):
        cur = self.conn.cursor()
        if not self.check_duplicate_artist(name):
            print("Adding new artist")
            id = [x for x in cur.execute("SELECT ar_id FROM artists")]
            cur.execute("INSERT INTO artists values (?,?)", (max(id)[0] + 1, name))
            self.conn.commit()

    def check_duplicate_songs(self, name):
        cur = self.conn.cursor()
        # print(name)
        songs = cur.execute(f'SELECT song_name FROM songs WHERE song_name = "{name}"')
        songs = [x for x in songs]
        # print(songs)
        if songs:
            print(f"Detected duplicate song : {name}")
            return True
        else:
            return False

    def check_duplicate_artist(self, name):
        cur = self.conn.cursor()
        songs = cur.execute(f'SELECT ar_name FROM artists WHERE ar_name = "{name}"')
        songs = [x for x in songs]
        if songs:
            print(f"Detected duplicate artist : {name}")
            return True
        else:
            return False




db = Database("Musics.db")
player = SongDownload("C:\\Users\grand\Documents\Music", db)
for x in ["Jordan Comolli", "Bassjackers", "BlasterJaxx"]:
    player.download_artist(x)