from ovos_utils.skills.templates.video_collection import VideoCollectionSkill
from mycroft.skills.core import intent_file_handler
from pyvod import Collection, Media
from os.path import join, dirname, basename
from ovos_utils.playback import CPSMatchType, CPSPlayback, CPSMatchConfidence


class DustSkill(VideoCollectionSkill):

    def __init__(self):
        super().__init__("Dust")
        self.supported_media = [CPSMatchType.GENERIC,
                                CPSMatchType.MOVIE,
                                CPSMatchType.TRAILER,
                                CPSMatchType.VIDEO]
        self.message_namespace = basename(dirname(__file__)) + ".jarbasskills"
        # load video catalog
        path = join(dirname(__file__), "res", "dust.jsondb")
        logo = join(dirname(__file__), "res", "dust_logo.png")
        self.media_collection = Collection("dust", logo=logo, db_path=path)
        self.default_image = join(dirname(__file__), "ui", "dust_icon.png")
        self.skill_logo = join(dirname(__file__), "ui", "dust_icon.png")
        self.skill_icon = join(dirname(__file__), "ui", "dust_icon.png")
        self.default_bg = logo
        self.media_type = CPSMatchType.MOVIE

    # voice interaction
    def get_intro_message(self):
        self.speak_dialog("intro")

    @intent_file_handler('home.intent')
    def handle_homescreen_utterance(self, message):
        self.handle_homescreen(message)

    # better common play
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

    def match_media_type(self, phrase, media_type):
        score = 0
        if self.voc_match(phrase, "video") or media_type == CPSMatchType.VIDEO:
            score += 5

        if self.voc_match(phrase, "short"):
            score += 5

        if self.voc_match(phrase, "scifi"):
            score += 50
            if self.voc_match(phrase, "dust"):
                score += 40

        if self.voc_match(phrase, "horror"):
            score += 5

        if self.voc_match(phrase, "movie") or media_type == CPSMatchType.MOVIE:
            score += 10

        if self.voc_match(phrase, "dust"):
            score += 10

        return score

    def match_title(self, video, phrase, media_type):
        score = super().match_title(video, phrase, media_type)
        if media_type == CPSMatchType.TRAILER and \
                not self.voc_match(video["title"], "trailer"):
            score = 0
        elif self.voc_match(video["title"], "trailer"):
            score -= 30
        return score


def create_skill():
    return DustSkill()

