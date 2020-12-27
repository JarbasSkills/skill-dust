from ovos_utils.waiting_for_mycroft.common_play import CommonPlaySkill, \
    CPSMatchLevel, CPSTrackStatus, CPSMatchType
from ovos_utils.skills.templates.media_collection import MediaCollectionSkill
from mycroft.skills.core import intent_file_handler
from mycroft.util.parse import fuzzy_match, match_one
from pyvod import Collection, Media
from os.path import join, dirname, basename
import random
import re
from json_database import JsonStorageXDG
import datetime


class DustSkill(MediaCollectionSkill):

    def __init__(self):
        super().__init__("Dust")
        self.supported_media = [CPSMatchType.GENERIC,
                                CPSMatchType.MOVIE,
                                CPSMatchType.VIDEO]
        self.message_namespace = basename(dirname(__file__)) + ".jarbasskills"
        # load video catalog
        path = join(dirname(__file__), "res", "dust.jsondb")
        logo = join(dirname(__file__), "res", "dust_logo.png")
        self.media_collection = Collection("dust", logo=logo, db_path=path)

    # voice interaction
    def get_intro_message(self):
        self.speak_dialog("intro")

    @intent_file_handler('dusthome.intent')
    def handle_homescreen_utterance(self, message):
        self.handle_homescreen(message)

    # matching
    def match_media_type(self, phrase, media_type):
        match = None
        score = 0

        if self.voc_match(phrase,
                          "video") or media_type == CPSMatchType.VIDEO:
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
            score += 0.1
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase, "dust"):
            score += 0.3
            match = CPSMatchLevel.TITLE

        return match, score

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

    def calc_final_score(self, phrase, base_score, match_level):
        score = base_score
        if self.voc_match(phrase, "dust"):
            score += 0.15
        if self.voc_match(phrase, "short"):
            score += 0.05
            if self.voc_match(phrase, "movie"):
                score += 0.05  # bonus for short films

        # optionally return new match_level
        # return score, match_level
        return score


def create_skill():
    return DustSkill()