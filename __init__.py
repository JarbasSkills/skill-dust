import random
from os.path import join, dirname

import requests
from json_database import JsonStorageXDG

from ovos_utils.ocp import MediaType, PlaybackType
from ovos_workshop.decorators.ocp import ocp_search, ocp_featured_media
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill


class DustSkill(OVOSCommonPlaybackSkill):

    def __init__(self, *args, **kwargs):
        self.supported_media = [MediaType.SHORT_FILM]
        self.skill_icon = join(dirname(__file__), "ui", "dust_icon.png")
        self.archive = JsonStorageXDG("dust", subfolder="OCP")
        self.media_type_exceptions = {
            # url 2 MediaType , if not present its a short film
        }
        super().__init__(*args, **kwargs)

    def initialize(self):
        self._sync_db()
        self.load_ocp_keywords()

    def load_ocp_keywords(self):
        titles = []
        series_name = []
        docu_name = []
        podcast_name = []

        for url, data in self.archive.items():

            if "Series" in data["title"] and "Podcast" not in data["title"]:
                t = data["title"].split("Series")[1].split("| DUST")[0].replace("“", '"').replace("”", '"').strip()
                if ' Episode' in t:
                    title, n = t.split(' Episode')
                    title = title.replace('"', "").replace('|', "").strip()
                    # we can parse episode number and name if wanted
                    # if ":" in n:
                    #    n, epi = n.split(":")
                    series_name.append(title)
                elif ' Part' in t:
                    if ":" in t:
                        t, n = t.split(":")
                    if " Part " in t:
                        t, n = t.split(" Part ")
                    t = t.strip()[1:]
                    if '" ' in t:
                        t, epi = t.split('" ')
                    else:
                        t = t[:-1]
                    series_name.append(t)
                elif ' Ep ' in t:
                    t, n = t.split(" Ep ")
                    series_name.append(t.replace('"', ""))
                elif not t.strip() or t.startswith(":") or t.startswith("|"):
                    continue
                else:
                    t = t.split(" Epilogue")[0].split(" Complete")[0].replace('"', "")
                    series_name.append(t)
                # signal this entry as VIDEO_EPISODES media type
                # in case it gets selected later
                self.media_type_exceptions[data["url"]] = MediaType.VIDEO_EPISODES
                continue

            if any(_ in data["title"].lower() for _ in ["interviews", "making of", "behind the scenes"]):
                t = data["title"].split("|")[1].strip()
                # signal this entry as BTS media type
                # in case it gets selected later
                self.media_type_exceptions[data["url"]] = MediaType.BEHIND_THE_SCENES
                series_name.append(t)
            else:
                t = data["title"].split("|")[0].split("(")[0].replace("“", '"').replace("”", '"')
                if '"' in t:
                    title = t.split('"')[1].strip()
                    if title:
                        if "podcast" in data["title"].lower():
                            # parse episode if wanted
                            # if " | Part" in data["title"]:
                            #    t, epi = data["title"].split(" | Part")
                            # elif " | Episode" in data["title"]:
                            #    t, epi = data["title"].split(" | Episode")
                            # else:
                            #    epi = data["title"].split(" | ")[1]
                            # epi = epi.split("|")[0].strip()
                            # if epi[0].isdigit():
                            #    n = epi[0]
                            #    epi = epi[1:].replace(': ', "").replace('- ', "").replace('"', "").strip()
                            # elif " - " in epi:
                            #    n, epi = epi.split(" - ")
                            # elif ": " in epi:
                            #    n, epi = epi.split(": ", 1)
                            podcast_name.append(title)
                            self.media_type_exceptions[data["url"]] = MediaType.PODCAST
                        elif "documentary" in data["title"].lower():
                            docu_name.append(title)
                            self.media_type_exceptions[data["url"]] = MediaType.DOCUMENTARY
                        else:
                            titles.append(title)

        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "short_movie_name", titles)
        self.register_ocp_keyword(MediaType.DOCUMENTARY,
                                  "documentary_name", docu_name)
        self.register_ocp_keyword(MediaType.VIDEO_EPISODES,
                                  "series_name", series_name)
        self.register_ocp_keyword(MediaType.PODCAST,
                                  "podcast_name", podcast_name)
        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "shorts_streaming_provider",
                                  ["Dust"])

    def _sync_db(self):
        bootstrap = "https://github.com/JarbasSkills/skill-dust/raw/dev/bootstrap.json"
        data = requests.get(bootstrap).json()
        self.archive.merge(data)
        self.schedule_event(self._sync_db, random.randint(3600, 24 * 3600))

    def get_playlist(self, num_entries=50):
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
        base_score = 25 if media_type == MediaType.SHORT_FILM else 0
        entities = self.ocp_voc_match(phrase)
        base_score += 50 * len(entities)

        title = entities.get("short_movie_name")
        skill = "shorts_streaming_provider" in entities  # skill matched

        # handle media_type per entry
        if media_type == MediaType.PODCAST:
            candidates = [video for video in self.archive.values()
                          if self.media_type_exceptions.get(video["url"], MediaType.SHORT_FILM) ==
                          MediaType.PODCAST]
        elif media_type == MediaType.VIDEO_EPISODES:
            candidates = [video for video in self.archive.values()
                          if self.media_type_exceptions.get(video["url"], MediaType.SHORT_FILM) ==
                          MediaType.VIDEO_EPISODES]
        elif media_type == MediaType.DOCUMENTARY:
            candidates = [video for video in self.archive.values()
                          if self.media_type_exceptions.get(video["url"], MediaType.SHORT_FILM) ==
                          MediaType.DOCUMENTARY]
        elif media_type == MediaType.BEHIND_THE_SCENES:
            candidates = [video for video in self.archive.values()
                          if self.media_type_exceptions.get(video["url"], MediaType.SHORT_FILM) ==
                          MediaType.BEHIND_THE_SCENES]
        else:
            candidates = [video for video in self.archive.values()
                          if video["url"] not in self.media_type_exceptions]

        if title:
            # only search db if user explicitly requested short films
            if title:
                candidates = [video for video in candidates
                              if title.lower() in video["title"].lower()]

                for video in candidates:
                    yield {
                        "title": video["title"],
                        "artist": video["author"],
                        "match_confidence": min(100, base_score),
                        "media_type": self.media_type_exceptions.get(video["url"], MediaType.SHORT_FILM),
                        "uri": "youtube//" + video["url"],
                        "playback": PlaybackType.VIDEO,
                        "skill_icon": self.skill_icon,
                        "skill_id": self.skill_id,
                        "image": video["thumbnail"],
                        "bg_image": video["thumbnail"],
                    }

        if skill:
            yield self.get_playlist()

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
        } for video in self.archive.values()
            if video["url"] not in self.media_type_exceptions]


if __name__ == "__main__":
    from ovos_utils.messagebus import FakeBus

    s = DustSkill(bus=FakeBus(), skill_id="t.fake")
    for r in s.search_db("play First Contact", MediaType.MOVIE):
        print(r)
        # {'title': 'Sci-Fi Short Film: "Eye Contact" | DUST', 'author': 'DUST', 'match_confidence': 50, 'media_type': <MediaType.SHORT_FILM: 17>, 'uri': 'youtube//https://youtube.com/watch?v=FxhrFPusEu8', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/FxhrFPusEu8/sddefault.jpg', 'bg_image': 'https://i.ytimg.com/vi/FxhrFPusEu8/sddefault.jpg'}
        # {'title': 'Animated Sci-Fi Short Film “Contact” | DUST', 'author': 'DUST', 'match_confidence': 50, 'media_type': <MediaType.SHORT_FILM: 17>, 'uri': 'youtube//https://youtube.com/watch?v=8Fj6hUIirSw', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/8Fj6hUIirSw/sddefault.jpg', 'bg_image': 'https://i.ytimg.com/vi/8Fj6hUIirSw/sddefault.jpg'}
        # {'title': 'Sci-Fi Short Film “Contact" | DUST', 'author': 'DUST', 'match_confidence': 50, 'media_type': <MediaType.SHORT_FILM: 17>, 'uri': 'youtube//https://youtube.com/watch?v=GhDlV9PDw3Y', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/GhDlV9PDw3Y/sddefault.jpg', 'bg_image': 'https://i.ytimg.com/vi/GhDlV9PDw3Y/sddefault.jpg'}
    for r in s.search_db("play First Contact", MediaType.PODCAST):
        print(r)
        # {'title': 'Sci-Fi Podcast "CHRYSALIS" | Part Thirteen: Contact | DUST', 'author': 'DUST', 'match_confidence': 50, 'media_type': <MediaType.PODCAST: 6>, 'uri': 'youtube//https://youtube.com/watch?v=wovLc6pIt6s', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/wovLc6pIt6s/sddefault.jpg', 'bg_image': 'https://i.ytimg.com/vi/wovLc6pIt6s/sddefault.jpg'}
