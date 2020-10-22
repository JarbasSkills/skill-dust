from mycroft.skills.common_play_skill import CommonPlaySkill, \
    CPSMatchLevel, CPSTrackStatus, CPSMatchType
from mycroft.skills.core import intent_file_handler
from mycroft.util.parse import fuzzy_match, match_one
from pyvod import Collection, Media
from os.path import join, dirname
import random
import re
from json_database import JsonStorageXDG


class DUSTSkill(CommonPlaySkill):

    def __init__(self):
        super().__init__("Dust")
        self.supported_media = [CPSMatchType.GENERIC,
                                CPSMatchType.VIDEO,
                                CPSMatchType.TRAILER,
                                CPSMatchType.MOVIE]

        # database update
        path = join(dirname(__file__), "res", "dust.jsondb")

        # load video catalog
        self.dust = Collection("Dust",
                               logo=join(dirname(__file__), "res",
                                         "dust_logo.png"),
                               db_path=path)
        self.videos = [ch.as_json() for ch in self.dust.entries]
        self.videos = sorted(self.videos, key=lambda kv: kv["rating"],
                             reverse=True)

    def initialize(self):
        self.add_event('skill-dust.jarbasskills.home',
                       self.handle_homescreen)
        self.gui.register_handler("skill-dust.jarbasskills.play_event",
                                  self.play_video_event)
        self.gui.register_handler("skill-dust.jarbasskills.clear_history",
                                  self.handle_clear_history)

    def get_intro_message(self):
        self.speak_dialog("intro")

    @intent_file_handler('dusthome.intent')
    def handle_homescreen_utterance(self, message):
        self.handle_homescreen(message)

    # homescreen
    def handle_homescreen(self, message):
        videos = list(self.videos)
        videos = [v for v in videos if "trailer" not in v[
                "full_title"].lower()]
        videos = [v for v in videos if "behind the scenes" not in v[
            "full_title"].lower()]
        videos = [v for v in videos if "the making of" not in v[
            "full_title"].lower()]
        videos = [v for v in videos if "exclusive clip" not in v[
            "full_title"].lower()]
        self.gui.clear()
        self.gui["mytvtogoHomeModel"] = videos
        self.gui["historyModel"] = JsonStorageXDG("dust-history").get("model", [])
        self.gui.show_page("Homescreen.qml", override_idle=True)

    # play GUI event
    def play_video_event(self, message):
        video_data = message.data["modelData"]
        self.play_dust(video_data)

    # clear history GUI event
    def handle_clear_history(self, message):
        historyDB = JsonStorageXDG("dust-history")
        historyDB["model"] = []
        historyDB.store()

    # common play
    def play_dust(self, video_data):
        if not self.gui.connected:
            self.log.error("GUI is required for DUST skill, "
                           "but no GUI connection was detected")
            raise RuntimeError
        # add to playback history

        # History
        historyDB = JsonStorageXDG("dust-history")
        if "model" not in historyDB:
            historyDB["model"] = []
        historyDB["model"].append(video_data)
        historyDB.store()

        self.gui["historyModel"] = historyDB["model"]
        # play video
        video = Media.from_json(video_data)
        url = str(video.streams[0])
        self.gui.play_video(url, video.name)

    def remove_voc(self, utt, voc_filename, lang=None):
        lang = lang or self.lang
        cache_key = lang + voc_filename

        if cache_key not in self.voc_match_cache:
            # trigger caching
            self.voc_match(utt, voc_filename, lang)

        if utt:
            # Check for matches against complete words
            for i in self.voc_match_cache[cache_key]:
                # Substitute only whole words matching the token
                utt = re.sub(r'\b' + i + r"\b", "", utt)

        return utt

    def match_media_type(self, phrase, media_type):
        match = None
        score = 0

        if self.voc_match(phrase,
                          "video") or media_type == CPSMatchType.VIDEO:
            score += 0.1
            match = CPSMatchLevel.GENERIC

        if media_type == CPSMatchType.TRAILER:
            score += 0.05
            match = CPSMatchLevel.GENERIC

        if self.voc_match(phrase, "short"):
            score += 0.15
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase, "scifi"):
            score += 0.1
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase, "horror"):
            score += 0.05
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase,
                          "movie") or media_type == CPSMatchType.MOVIE:
            score += 0.2
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase, "dust"):
            score += 0.2
            match = CPSMatchLevel.TITLE

        return match, score

    def _clean_title(self, title):
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
        return title

    def CPS_match_query_phrase(self, phrase, media_type):
        leftover_text = phrase
        best_score = 0

        # dont match if gui is not connected
        if not self.gui.connected:
            return None

        # see if media type is in query, base_score will depend if "scifi"
        # or "video" is in query
        match, base_score = self.match_media_type(phrase, media_type)

        videos = list(self.videos)
        if self.voc_match(phrase, "trailer") or \
                media_type == CPSMatchType.TRAILER:
            videos = [v for v in videos if "trailer" in v[
                "full_title"].lower()]
        else:
            videos = [v for v in videos if "trailer" not in v[
                "full_title"].lower()]

        best_video = random.choice(videos)

        # score video data
        for ch in videos:
            score = 0
            # score tags
            tags = list(set(ch.get("tags", [])))
            if tags:
                # tag match bonus
                for tag in tags:
                    tag = tag.lower().strip()
                    if tag in phrase and tag != "dust":
                        match = CPSMatchLevel.CATEGORY
                        score += 0.2
                        leftover_text = leftover_text.replace(tag, "")

            # score description
            words = ch.get("summary", "").split(" ")
            for word in words:
                if len(word) > 4 and word in leftover_text:
                    score += 0.05

            if score > best_score:
                best_video = ch
                best_score = score

        # match video name
        for ch in videos:
            title = self._clean_title(ch["full_title"])

            score = fuzzy_match(leftover_text, title)
            if score >= best_score:
                # TODO handle ties
                match = CPSMatchLevel.TITLE
                best_video = ch
                best_score = score
                leftover_text = title

        if not best_video:
            self.log.debug("No DUST matches")
            return None

        if best_score < 0.6:
            self.log.debug("Low score, randomizing results")
            best_video = random.choice(videos)

        score = base_score + best_score

        if self.voc_match(phrase, "dust"):
            score += 0.15
        if self.voc_match(phrase, "short"):
            score += 0.05
            if self.voc_match(phrase, "movie"):
                score += 0.05  # bonus for short films

        if score >= 0.85:
            match = CPSMatchLevel.EXACT
        elif score >= 0.7:
            match = CPSMatchLevel.MULTI_KEY
        elif score >= 0.5:
            match = CPSMatchLevel.TITLE

        self.log.debug("Best DUST video: " + best_video["full_title"])

        if match is not None:
            return (leftover_text, match, best_video)
        return None

    def CPS_start(self, phrase, data):
        self.play_dust(data)


def create_skill():
    return DUSTSkill()
