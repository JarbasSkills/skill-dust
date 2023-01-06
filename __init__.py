from os.path import join, dirname
import random

from ovos_utils.log import LOG
from ovos_utils.parse import fuzzy_match
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    ocp_search, ocp_featured_media, MediaType, PlaybackType
from youtube_archivist import YoutubeMonitor


class DustSkill(OVOSCommonPlaybackSkill):

    def __init__(self):
        super().__init__("Dust")
        self.supported_media = [MediaType.MOVIE,
                                MediaType.GENERIC,
                                MediaType.SHORT_FILM,
                                MediaType.VIDEO]
        self.archive = YoutubeMonitor("dust",
                                      blacklisted_kwords=["trailer"],
                                      logger=LOG)
        self.skill_icon = join(dirname(__file__), "ui", "dust_icon.png")

    def initialize(self):
        bootstrap = "https://github.com/JarbasSkills/skill-dust/raw/dev/bootstrap.json"
        self.archive.bootstrap_from_url(bootstrap)
        self.schedule_event(self._sync_db, random.randint(3600, 24 * 3600))

    def _sync_db(self):
        url = "https://www.youtube.com/c/watchdust"
        self.archive.parse_videos(url)
        self.schedule_event(self._sync_db, random.randint(3600, 24*3600))

    def normalize_title(self, title):
        title = title.lower().strip()
        title = self.remove_voc(title, "dust")
        title = self.remove_voc(title, "movie")
        title = self.remove_voc(title, "video")
        title = self.remove_voc(title, "scifi")
        title = self.remove_voc(title, "short")
        title = self.remove_voc(title, "horror")
        title = title.replace("|", "").replace('"', "") \
            .replace(':', "").replace('”', "").replace('“', "") \
            .strip()
        return " ".join([w for w in title.split(" ") if w])  # remove extra spaces

    def match_skill(self, phrase, media_type):
        score = 0
        if self.voc_match(phrase, "scifi"):
            score += 15
        if self.voc_match(phrase, "horror"):
            score += 5
        if self.voc_match(phrase, "dust"):
            score += 40
        if media_type == MediaType.SHORT_FILM:
            score += 25
        return score

    def calc_score(self, phrase, match, base_score=0):
        score = base_score
        score += 100 * fuzzy_match(phrase.lower(), match["title"].lower())
        return min(100, score)

    def get_playlist(self, num_entries=250):
        return {
            "match_confidence": 70,
            "media_type": MediaType.SHORT_FILM,
            "playlist": self.featured_media()[:num_entries],
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "image": self.skill_icon,
            "title": "Dust (Short Films Playlist)",
            "author": "Dust"
        }

    @ocp_search()
    def search_db(self, phrase, media_type):
        if self.voc_match(phrase, "dust"):
            pl = self.get_playlist()
            if self.voc_match(phrase, "dust", exact=True):
                pl["match_confidence"] = 100
            yield pl

        if media_type == MediaType.SHORT_FILM:
            # only search db if user explicitly requested short films
            base_score = self.match_skill(phrase, media_type)
            phrase = self.normalize_title(phrase)
            for url, video in self.archive.db.items():
                yield {
                    "title": video["title"],
                    "match_confidence": self.calc_score(phrase, video, base_score),
                    "media_type": MediaType.SHORT_FILM,
                    "uri": "youtube//" + url,
                    "playback": PlaybackType.VIDEO,
                    "skill_icon": self.skill_icon,
                    "skill_id": self.skill_id,
                    "image": video["thumbnail"],
                    "bg_image": video["thumbnail"],
                }

    @ocp_featured_media()
    def featured_media(self):
        return [{
            "title": video["title"],
            "image": video["thumbnail"],
            "match_confidence": 70,
            "media_type": MediaType.SHORT_FILM,
            "uri": "youtube//" + video["url"],
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "bg_image": video["thumbnail"],
            "skill_id": self.skill_id
        } for video in self.archive.sorted_entries()]


def create_skill():
    return DustSkill()
