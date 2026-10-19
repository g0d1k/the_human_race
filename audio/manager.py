"""Audio front-end: builds every Sound at startup, then plays music and SFX.

If the mixer is unavailable (no audio device, init failure) every method is
a harmless no-op so the game runs silently.
"""
import pygame

from audio.apu import APU, levels_to_buffer, render_sfx
from audio.mml import render_song
from audio.songs import SONGS
from audio.sfx import build_sfx_frames

MUSIC_GAIN = 0.85
SFX_GAIN = 1.0

# dedicated channels so rapid effects don't starve each other
CH_MUSIC = 0
CH_SHOT = (1, 2)
CH_ENEMY = 3
CH_SIREN = 4
NUM_RESERVED = 5


class Audio:
    def __init__(self, settings):
        self.settings = settings
        self.ok = False
        self.sounds = {}
        self.music = {}
        self.current_music = None
        self.music_loop = True
        self.paused = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            init = pygame.mixer.get_init()
            if init:
                self.rate, self.fmt, self.channels = init
                pygame.mixer.set_num_channels(16)
                pygame.mixer.set_reserved(NUM_RESERVED)
                self.ok = True
        except (pygame.error, NotImplementedError, AttributeError, OSError):
            self.ok = False

    def _sound(self, levels, gain):
        buf = levels_to_buffer(levels, self.fmt, self.channels, gain)
        return pygame.mixer.Sound(buffer=buf)

    def build(self):
        """Generator: renders all audio, yielding progress fractions."""
        if not self.ok:
            yield 1.0
            return
        try:
            apu = APU(self.rate)
            frames = build_sfx_frames()
            total = len(frames) + len(SONGS)
            done = 0
            for name, fr in frames.items():
                self.sounds[name] = self._sound(render_sfx(apu, fr), SFX_GAIN)
                done += 1
                yield done / float(total)
            for name, sng in SONGS.items():
                self.music[name] = (self._sound(render_song(apu, sng), MUSIC_GAIN), sng.get("loop", True))
                done += 1
                yield done / float(total)
            self.apply_volumes()
        except (pygame.error, ValueError, MemoryError, OSError):
            # Something about this audio device is unusable: go silent.
            self.ok = False
            self.sounds = {}
            self.music = {}
            yield 1.0

    # ------------------------------------------------------------------
    def apply_volumes(self):
        if not self.ok:
            return
        mv = self.settings["music_volume"] / 10.0
        sv = self.settings["sfx_volume"] / 10.0
        try:
            for snd, _ in self.music.values():
                snd.set_volume(mv)
            for snd in self.sounds.values():
                snd.set_volume(sv)
        except pygame.error:
            pass

    def play_music(self, name, restart=False):
        if not self.ok or name not in self.music:
            return
        if self.current_music == name and not restart and self.music_busy():
            return
        snd, loop = self.music[name]
        try:
            pygame.mixer.Channel(CH_MUSIC).play(snd, loops=-1 if loop else 0)
        except pygame.error:
            return
        self.current_music = name
        self.music_loop = loop

    def music_busy(self):
        if not self.ok:
            return False
        try:
            return pygame.mixer.Channel(CH_MUSIC).get_busy()
        except pygame.error:
            return False

    def stop_music(self):
        self.current_music = None
        if self.ok:
            try:
                pygame.mixer.Channel(CH_MUSIC).stop()
            except pygame.error:
                pass

    def play(self, name, channel=None, loops=0):
        if not self.ok:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        try:
            if channel is not None:
                pygame.mixer.Channel(channel).play(snd, loops=loops)
            else:
                ch = pygame.mixer.find_channel(True)
                if ch is not None:
                    ch.play(snd, loops=loops)
        except pygame.error:
            pass

    def shot(self, player_index, name):
        self.play(name, CH_SHOT[player_index & 1])

    def enemy_shot(self):
        self.play("enemy_shot", CH_ENEMY)

    def siren(self, on):
        if not self.ok:
            return
        try:
            if on:
                self.play("siren", CH_SIREN, loops=-1)
            else:
                pygame.mixer.Channel(CH_SIREN).stop()
        except pygame.error:
            pass

    def pause_all(self):
        if self.ok and not self.paused:
            try:
                pygame.mixer.pause()
            except pygame.error:
                pass
        self.paused = True

    def resume_all(self):
        if self.ok and self.paused:
            try:
                pygame.mixer.unpause()
            except pygame.error:
                pass
        self.paused = False

    def stop_sfx(self):
        if not self.ok:
            return
        try:
            for i in range(1, pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(i).stop()
        except pygame.error:
            pass
