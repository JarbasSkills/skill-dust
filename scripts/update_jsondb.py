from youtube_archivist import YoutubeMonitor
import shutil
from os.path import dirname

url = "https://www.youtube.com/c/watchdust"
archive = YoutubeMonitor("dust",
                         blacklisted_kwords=["trailer"])

archive.parse_videos(url)

shutil.copy(archive.db.path, f"{dirname(dirname(__file__))}/bootstrap.json")
