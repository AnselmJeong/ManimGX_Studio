"""Sound placement and edits, and speech timing, captions and voices."""

from fractions import Fraction
from pathlib import Path
from typing import cast

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

import manimgx as m
from manimgx.animation import clock
from manimgx.audio import sound as voices
from manimgx.audio.sound import (
    CUT,
    RATE,
    Clip,
    Speech,
    Word,
    cached,
    estimate,
    lines,
    mix,
    spans,
    timed,
    times,
)
from manimgx.config import config


def tone(seconds: float = 0.1, level: float = 0.5) -> m.Sound:
    t = np.arange(round(seconds * RATE)) / RATE
    return m.Sound((level * np.sin(2 * np.pi * 440 * t)).astype(np.float32), rate=RATE)


def click() -> m.Sound:
    x = np.zeros(480, np.float32)
    x[0] = 1.0
    return m.Sound(x, rate=RATE)


def test_a_stop_keeps_its_time_until_audio_is_sampled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(clock, "now", Fraction(3, 10))
    clip = Clip(click(), Fraction(0))
    clip.stop(1e-8)
    assert clip.end == Fraction(3, 10) + Fraction(1, 100000000)


def starts(scene: type[m.Scene], fps: float) -> list[Fraction]:
    saved = config.frame_rate
    config.frame_rate = fps
    try:
        return [clip.start for clip in scene().render().clips]
    finally:
        config.frame_rate = saved


class TestPlacement:
    @settings(max_examples=40)
    @given(
        lag=st.sampled_from([0.0, 0.25, 0.3, 0.5, 1.0]),
        run_time=st.sampled_from([0.3, 0.55, 1.0, 1.3]),
        count=st.integers(1, 5),
    )
    def test_a_sound_in_a_composition_starts_as_its_window_opens(
        self, lag: float, run_time: float, count: int
    ) -> None:
        class Clicks(m.Scene):
            def construct(self) -> None:
                dots = [m.Dot(i * m.RIGHT) for i in range(count)]
                self.wait(0.37)  # a start between frames
                self.play(
                    m.LaggedStart(
                        *(
                            m.AnimationGroup(m.FadeIn(d, run_time=run_time), click())
                            for d in dots
                        ),
                        lag_ratio=lag,
                    )
                )

        begin = Fraction(37, 100)
        span = Fraction(run_time).limit_denominator(10**6)
        step = span * Fraction(lag).limit_denominator(10**6)
        want = [begin + i * step for i in range(count)]
        assert starts(Clicks, 30) == want
        assert starts(Clicks, 10) == want
        assert starts(Clicks, 24) == want

    def test_a_sound_added_by_an_updater_starts_at_its_step(self) -> None:
        class Bounce(m.Scene):
            def construct(self) -> None:
                ball = m.Dot(2 * m.UP)
                state = {"v": 0.0}

                def fall(mob: m.Mobject, dt: float) -> None:
                    state["v"] -= 9.8 * dt
                    mob.shift(state["v"] * dt * m.UP)
                    if mob.get_y() < -2 and state["v"] < 0:
                        state["v"] = -0.8 * state["v"]
                        self.add_sound(click())

                ball.add_updater(fall)
                self.add(ball)
                self.wait(3)

        at_60, at_10 = starts(Bounce, 60), starts(Bounce, 10)
        assert at_60
        assert at_60 == at_10  # on the simulation clock, not the frames
        assert all((t * 60).denominator == 1 for t in at_60)

    def test_a_play_of_sounds_lasts_as_long_as_its_longest(self) -> None:
        class Sounds(m.Scene):
            def construct(self) -> None:
                self.play(tone(0.25), tone(0.75))

        film = Sounds().render()
        assert film.plays[0].end == Fraction(3, 4)
        assert [c.start for c in film.clips] == [0, 0]

    def test_a_play_run_time_does_not_stretch_a_sound(self) -> None:
        class Sounds(m.Scene):
            def construct(self) -> None:
                self.play(m.FadeIn(m.Dot()), tone(0.75), run_time=0.25)

        film = Sounds().render()
        assert film.plays[0].end == Fraction(3, 4)
        assert film.clips[0].sound.duration == 0.75

    def test_add_sound_takes_no_time(self) -> None:
        class Added(m.Scene):
            def construct(self) -> None:
                self.wait(0.5)
                self.add_sound(tone(2.0), time_offset=0.25)
                self.wait(0.5)

        film = Added().render()
        assert film.clips[0].start == Fraction(3, 4)
        assert film.plays[-1].end == 1

    def test_an_endless_sound_is_added_not_played(self) -> None:
        class Endless(m.Scene):
            def construct(self) -> None:
                self.play(tone().loop())

        with pytest.raises(ValueError, match="never ends: add it with add_sound"):
            Endless().render()

    def test_a_missing_file_fails_where_it_is_given(self) -> None:
        with pytest.raises(FileNotFoundError, match="no sound file"):
            m.Sound("no/such/sound.wav")


class TestEdits:
    @pytest.mark.parametrize("shape", [(0,), (0, 1), (0, 2)])
    def test_empty_samples_have_zero_duration(self, shape: tuple[int, ...]) -> None:
        sound = m.Sound(np.empty(shape, np.float32), rate=RATE)
        assert sound.duration == 0
        assert sound.samples.shape == (0, 1 if len(shape) == 1 else shape[1])

    @given(decibels=st.floats(-60, 60), more=st.floats(-60, 60))
    def test_gain_is_decibels(self, decibels: float, more: float) -> None:
        a = tone()
        np.testing.assert_allclose(
            a.gain(decibels).samples, a.samples * 10 ** (decibels / 20), rtol=1e-6
        )
        np.testing.assert_allclose(
            a.gain(decibels).gain(more).samples,
            a.gain(decibels + more).samples,
            rtol=1e-6,
        )

    def test_fades_ramp_from_and_to_silence(self) -> None:
        x = m.Sound(np.ones(RATE, np.float32), rate=RATE).fade_in(0.5).fade_out(0.25)
        s = x.samples[:, 0]
        assert s[0] == 0
        assert abs(s[RATE // 4] - 0.5) < 1e-3
        assert s[RATE // 2] == 1
        assert abs(s[-RATE // 8] - 0.5) < 1e-3
        assert s[-1] < 1e-3

    @given(start=st.floats(0, 1), end=st.none() | st.floats(0, 1))
    def test_a_trim_is_the_span_of_the_source(
        self, start: float, end: float | None
    ) -> None:
        x = m.Sound(np.arange(RATE, dtype=np.float32) / RATE, rate=RATE)
        span = slice(round(start * RATE), None if end is None else round(end * RATE))
        trimmed = x.trim(start, end)
        np.testing.assert_array_equal(trimmed.samples, x.samples[span])
        assert trimmed.duration == len(x.samples[span]) / RATE

    def test_a_loop_repeats_to_its_duration(self) -> None:
        looped = tone(0.1).loop(0.35)
        assert looped.duration == 0.35
        assert len(looped.samples) == round(0.35 * RATE)
        assert np.array_equal(looped.samples[:4800], looped.samples[4800:9600])

    def test_speed_shortens_the_sound(self) -> None:
        assert tone(1.0).speed(2).duration == pytest.approx(0.5, abs=1 / RATE)

    def test_pan_balances_left_and_right(self) -> None:
        left = tone().pan(-1).samples
        assert left.shape[1] == 2
        assert np.abs(left[:, 1]).max() == 0
        assert np.allclose(left[:, 0], tone().samples[:, 0])


class TestMix:
    @pytest.mark.parametrize("loop", [False, True])
    @pytest.mark.parametrize("end", [Fraction(0), Fraction(1)])
    def test_a_clip_stopped_before_it_starts_is_silent(
        self, loop: bool, end: Fraction
    ) -> None:
        sound = m.Sound(np.ones(2 * RATE, np.float32), rate=RATE)
        if loop:
            sound = sound.loop()
        track = mix([Clip(sound, Fraction(1), end=end, fade=0)], Fraction(3))
        assert track is not None
        assert not track.any()

    def test_ducking_releases_when_speech_is_stopped(self) -> None:
        bed = m.Sound(np.ones(RATE, np.float32), rate=RATE).loop().duck(12)
        speech = Speech(np.zeros(RATE, np.float32), text="quiet", rate=RATE)
        track = mix(
            [Clip(bed, Fraction(0)), Clip(speech, Fraction(2), end=Fraction(11, 5))],
            Fraction(4),
        )
        assert track is not None
        assert track[round(2.1 * RATE), 0] == pytest.approx(10 ** (-12 / 20))
        assert track[round(2.8 * RATE), 0] == 1

    @settings(max_examples=50)
    @given(
        starts=st.lists(
            st.fractions(0, 2).map(lambda f: f.limit_denominator(600)),
            min_size=1,
            max_size=4,
        )
    )
    def test_each_clip_lands_on_its_sample_and_the_mix_is_their_sum(
        self, starts: list[Fraction]
    ) -> None:
        clips = [Clip(click(), start) for start in starts]
        track = mix(clips, Fraction(3))
        assert track is not None
        want = np.zeros(3 * RATE, np.float32)
        for start in starts:
            want[round(start * RATE)] += 1.0
        assert np.array_equal(track[:, 0], want)

    def test_mono_clips_make_a_mono_track_and_a_stereo_one_stereo(self) -> None:
        mono = mix([Clip(tone(), Fraction(0))], Fraction(1))
        stereo = mix(
            [Clip(tone(), Fraction(0)), Clip(tone().pan(1), Fraction(0))], Fraction(1)
        )
        assert mono is not None
        assert mono.shape[1] == 1
        assert stereo is not None
        assert stereo.shape[1] == 2
        assert mix([], Fraction(1)) is None

    def test_a_stopped_clip_fades_from_the_stop(self) -> None:
        bed = Clip(m.Sound(np.ones(RATE, np.float32), rate=RATE).loop(), Fraction(0))
        bed.end, bed.fade = Fraction(3, 2), 0.5
        track = mix([bed], Fraction(3))
        assert track is not None
        s = track[:, 0]
        assert s[RATE - 1] == 1
        assert abs(s[5 * RATE // 4] - 0.5) < 1e-3
        assert not s[3 * RATE // 2 :].any()

    def test_an_endless_loop_fades_where_its_clip_starts_and_ends(self) -> None:
        one = m.Sound(np.ones(RATE // 2, np.float32), rate=RATE)
        bed = Clip(one.fade_in(0.25).fade_out(0.5).loop(), Fraction(0))
        track = mix([bed], Fraction(3))
        assert track is not None
        s = track[:, 0]
        assert s[RATE // 8] == pytest.approx(0.5, abs=1e-3)  # the start's fade, once
        assert s[RATE // 2 + RATE // 8] == 1  # not again at the second round
        assert s[5 * RATE // 2] == pytest.approx(1.0, abs=1e-3)  # the end's fade begins
        assert s[-RATE // 4] == pytest.approx(0.5, abs=1e-3)

    def test_a_sound_the_film_cuts_short_fades_as_it_is_cut(self) -> None:
        tone_ = Clip(m.Sound(np.ones(2 * RATE, np.float32), rate=RATE), Fraction(0))
        track = mix([tone_], Fraction(1))
        assert track is not None
        assert track[-1, 0] < 0.01  # no click at the cut
        assert track[RATE - round(CUT * RATE) - 1, 0] == 1

    def test_a_ducking_clip_dips_under_speech_and_only_there(self) -> None:
        bed = Clip(
            m.Sound(np.ones(RATE, np.float32), rate=RATE).loop().duck(12), Fraction(0)
        )
        words = Speech(np.zeros(RATE, np.float32), text="quiet", rate=RATE)
        track = mix([bed, Clip(words, Fraction(2))], Fraction(5))
        assert track is not None
        s = track[:, 0]
        low = 10 ** (-12 / 20)
        assert s[RATE] == pytest.approx(1)  # long before
        assert s[5 * RATE // 2] == pytest.approx(low, rel=1e-3)  # during
        assert s[9 * RATE // 2] == pytest.approx(1)  # long after


def memory(a: np.ndarray) -> list[np.ndarray]:
    """The arrays an array's values live in: a masked array's data and its mask."""
    return [np.ma.getdata(a), np.ma.getmaskarray(a)] if np.ma.isMaskedArray(a) else [a]


def shares(a: np.ndarray, b: np.ndarray) -> bool:
    return any(np.shares_memory(x, y) for x in memory(a) for y in memory(b))


SOURCES = ("an array", "a view", "reversed", "read-only", "masked", "mapped")


@pytest.mark.parametrize("speaks", [False, True], ids=["sound", "speech"])
@pytest.mark.parametrize("kind", SOURCES)
def test_a_sounds_samples_are_its_own(kind: str, speaks: bool, tmp_path: Path) -> None:
    """A sound holds its samples as a value, from when it is made: making them (a speech's
    words too) leaves the source as it was; the source changing, before they are first
    read or after, changes them not, nor its edits'; they changing changes not the source;
    an edit is samples of its own."""
    values = np.linspace(-0.5, 0.5, 96, dtype=np.float32).reshape(48, 2)
    base = (
        np.memmap(tmp_path / "samples.bin", np.float32, "w+", shape=(48, 2))
        if kind == "mapped"
        else values.copy()
    )
    base[:] = values
    source = {
        "an array": base,
        "a view": base.view(),
        "reversed": base[::-1],
        "read-only": base.view(),
        "masked": np.ma.array(base, mask=np.zeros(base.shape, bool)),
        "mapped": base,
    }[kind]
    source.flags.writeable = kind != "read-only"
    held = np.array(source)
    sound = (
        Speech(source, text="one, two.", rate=RATE)
        if speaks
        else m.Sound(source, rate=RATE)
    )
    base[:] = 3  # the source changing before its samples are first read
    samples = sound.samples
    if isinstance(sound, Speech):
        assert [w.text for w in sound.words] == ["one,", "two."]
    np.testing.assert_array_equal(samples, held)
    assert not shares(samples, source)

    base[:] = 2
    if np.ma.isMaskedArray(source):
        np.ma.getmaskarray(source)[0, 0] = True  # its own mask, not a copy
    np.testing.assert_array_equal(samples, held)
    assert not np.ma.getmaskarray(samples).any()
    samples[:] = 4
    np.testing.assert_array_equal(base, np.full((48, 2), 2, np.float32))
    edited = sound.gain(0).samples
    np.testing.assert_array_equal(np.ma.getdata(edited), held)
    assert not shares(edited, samples)
    assert not shares(edited, source)


SECONDS_PER_LETTER = 0.05
HOP = RATE // 100  # the estimate hears loudness in 10 ms hops
PAUSES = {".": 6, "!": 6, "?": 6, ":": 6, ";": 6, ",": 3}  # letters' worth after a word


def said(text: str) -> Speech:
    """A voice that takes 0.05 s a letter (a space too) and knows when it says each word."""
    words, at = [], 0.0
    for word in text.split():
        start = text.index(word, round(at / SECONDS_PER_LETTER))
        words.append(
            Word(
                word,
                start * SECONDS_PER_LETTER,
                (start + len(word)) * SECONDS_PER_LETTER,
            )
        )
        at = words[-1].end
    samples = np.full(round(len(text) * SECONDS_PER_LETTER * RATE), 0.1, np.float32)
    return Speech(samples, text=text, words=words, rate=RATE)


@pytest.fixture
def cache_here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("manimgx.scene._voice_folder", lambda scene: tmp_path / "voice")
    return tmp_path / "voice"


class Begun(m.Animation):
    """An animation that notes the instant it begins."""

    def __init__(self, log: list[Fraction], run_time: float = 1.0) -> None:
        super().__init__(None, run_time=run_time)
        self.log = log

    def begin(self) -> None:
        self.log.append(clock.now)


@pytest.mark.usefixtures("cache_here")
class TestScript:
    @given(st.lists(st.text("abc ", min_size=0, max_size=6), min_size=1, max_size=5))
    @example(["Here is ", "a circle", " and ", "a square", "."])
    @example(["No spans."])
    @example(["An empty ", "", " span."])
    def test_the_text_is_the_script_without_its_brackets(
        self, parts: list[str]
    ) -> None:
        script = "".join(f"[{p}]" if i % 2 else p for i, p in enumerate(parts))
        text, found = spans(script)
        assert text == script.replace("[", "").replace("]", "")
        for (a, b), part in zip(found, parts[1::2], strict=True):
            assert text[a:b] == part

    def test_a_span_is_said_from_its_first_word_to_its_last(self) -> None:
        speech = said("the derivative of x squared is two x")
        text, (span,) = spans("the derivative of [x squared] is two x")
        assert text == speech.text
        a, b = times(speech, span)
        x, squared = speech.words[3], speech.words[4]
        assert (a, b) == (x.start, squared.end)


@pytest.mark.usefixtures("cache_here")
class TestSay:
    def test_each_animation_starts_as_its_words_start(self) -> None:
        begun: list[Fraction] = []
        spoken: list[Speech] = []

        class Say(m.Scene):
            voice = staticmethod(said)

            def construct(self) -> None:
                self.wait(0.37)  # between frames
                spoken.append(
                    self.say(
                        "here is [a dot] and [a square too]",
                        Begun(begun),
                        Begun(begun, 0.1),
                    )
                )

        film = Say().render()
        (speech,) = spoken
        want = [times(speech, (8, 13))[0], times(speech, (18, 30))[0]]
        assert [float(t) - 0.37 for t in begun] == pytest.approx(want)
        # the second lasts as long as its words (longer than its 0.1 s), the first 1 s
        end = max(speech.duration, want[0] + 1, times(speech, (18, 30))[1])
        assert float(film.plays[-1].end) - 0.37 == pytest.approx(end)

    def test_the_play_lasts_as_long_as_the_speech_or_its_animations(self) -> None:
        class Long(m.Scene):
            voice = staticmethod(said)

            def construct(self) -> None:
                self.say("a long sentence with many letters in it", m.FadeIn(m.Dot()))

        film = Long().render()
        speech = film.clips[0].sound
        assert float(film.plays[0].end) == pytest.approx(speech.duration)

    def test_one_animation_per_span(self) -> None:
        class Wrong(m.Scene):
            voice = staticmethod(said)

            def construct(self) -> None:
                self.say("[one] and [two]", m.FadeIn(m.Dot()))

        with pytest.raises(ValueError, match="2 bracketed spans for 1 animations"):
            Wrong().render()


@pytest.mark.usefixtures("cache_here")
class TestVoice:
    def test_a_function_set_on_the_scene_is_its_voice(self) -> None:
        class Plain(m.Scene):
            voice = said  # a plain function: not a method of the scene

            def construct(self) -> None:
                self.say("plain words")

        (clip,) = Plain().render().clips
        assert isinstance(clip.sound, Speech)
        assert clip.sound.text == "plain words"


@pytest.mark.usefixtures("cache_here")
class TestCache:
    def test_function_identity_keeps_code_but_not_source_locations(self) -> None:
        def voice(source: str, filename: str) -> voices.Voice:
            scope: dict[str, object] = {
                "__name__": "recorded_voice",
                "speak": said,
                "first_speaker": said,
                "second_speaker": said,
            }
            exec(compile(source, filename, "exec"), scope)
            return cast("voices.Voice", scope["voice"])

        source = (
            "def voice(text):\n    return speak(' '.join(w for w in text.split()))\n"
        )
        original = voices._identity(voice(source, "first.py"))
        assert voices._identity(voice("\n\n" + source, "second.py")) == original
        assert (
            voices._identity(voice(source.replace("' '", "'_'"), "first.py"))
            != original
        )
        first = "def voice(text):\n    return first_speaker(text)\n"
        second = first.replace("first_speaker", "second_speaker")
        assert voices._identity(voice(first, "voice.py")) != voices._identity(
            voice(second, "voice.py")
        )

    @pytest.mark.parametrize("kind", ["array", "bytes", "file"])
    def test_cached_speech_preserves_edits_and_word_times(
        self, kind: str, cache_here: Path, tmp_path: Path
    ) -> None:
        samples = np.linspace(-0.5, 0.5, RATE, dtype=np.float32)
        audio = voices._wav(samples)
        path = tmp_path / "source.wav"
        path.write_bytes(audio)

        def voice(text: str) -> Speech:
            source = samples if kind == "array" else audio if kind == "bytes" else path
            return (
                Speech(
                    source,
                    text=text,
                    words=[Word(text, 0.2, 0.3)],
                    rate=RATE if kind == "array" else None,
                )
                .trim(0.1, 0.4)
                .speed(2)
                .gain(-6)
                .pan(0.25)
                .fade_in(0.01)
                .fade_out(0.02)
                .loop(0.35)
                .duck(9)
            )

        first = cached(voice, "hello", cache_here)
        again = cached(voice, "hello", cache_here)
        assert first.duration == again.duration == 0.35
        assert first.words == again.words
        np.testing.assert_array_equal(first.samples, again.samples)
        np.testing.assert_array_equal(
            mix([Clip(first, Fraction(0))], Fraction(1)),
            mix([Clip(again, Fraction(0))], Fraction(1)),
        )

    def test_a_voice_speaks_each_text_once(self, cache_here: Path) -> None:
        calls: list[str] = []

        def counted(text: str) -> Speech:
            calls.append(text)
            return said(text)

        for _ in range(2):
            speech = cached(counted, "hello there", cache_here)
        assert calls == ["hello there"]
        assert [w.text for w in speech.words] == ["hello", "there"]
        assert (
            len(list(cache_here.glob("hello-there-*"))) == 2
        )  # the audio and its words
        (words,) = cache_here.glob("hello-there-*.json")
        assert words.read_text(encoding="utf-8").endswith("}\n")  # a text file's end

    def test_a_recording_in_its_place_is_timed_again(self, cache_here: Path) -> None:
        cached(said, "hello there", cache_here)
        (audio,) = cache_here.glob("hello-there-*.wav")
        silence_then_sound = np.concatenate(
            [np.zeros(RATE, np.float32), np.full(RATE, 0.5, np.float32)]
        )
        audio.write_bytes(voices._wav(silence_then_sound[:, None]))
        again = cached(said, "hello there", cache_here)
        assert again.words[0].start >= 0.9  # estimated from the recording, not kept

    def test_a_voice_is_named_by_what_it_holds_not_where(self) -> None:
        def speaking(pace: float):  # a voice factory: closures with the same name
            def voice(text: str) -> Speech:
                return said(text).speed(pace)

            return voice

        slow, fast, again = speaking(1.0), speaking(1.5), speaking(1.0)
        assert voices._identity(slow) != voices._identity(fast)
        assert voices._identity(slow) == voices._identity(again)

        class Called:  # a callable object: named by its fields, not its address
            def __init__(self, voice_id: str) -> None:
                self.voice_id = voice_id

            def __call__(self, text: str) -> Speech:
                return said(text)

        assert voices._identity(Called("a")) == voices._identity(Called("a"))
        assert voices._identity(Called("a")) != voices._identity(Called("b"))


@pytest.mark.usefixtures("cache_here")
class TestWords:
    def test_leading_punctuation_keeps_its_place_in_timed_text(self) -> None:
        text = "— hi"
        speech = Speech(
            np.zeros(RATE, np.float32),
            text=text,
            words=timed(text, [("hi", 0.1, 0.2)]),
            rate=RATE,
        )
        assert speech.words == (Word("—", 0.1, 0.1), Word("hi", 0.1, 0.2))
        assert times(speech, (2, 4)) == (0.1, 0.2)

    def test_pieces_time_the_words(self) -> None:
        pieces = [(c, i * 0.1, i * 0.1 + 0.1) for i, c in enumerate("hi, you")]
        hi, you = timed("hi, you", pieces)
        assert (hi.text, hi.start, hi.end) == ("hi,", 0.0, pytest.approx(0.2))
        assert (you.start, you.end) == (pytest.approx(0.4), pytest.approx(0.7))

    def test_other_letters_are_not_the_words(self) -> None:
        assert timed("2x", [("two", 0, 0.3), ("x", 0.3, 0.5)]) == ()

    @given(
        words=st.lists(
            st.builds(
                str.__add__,
                st.text("aé世", min_size=1, max_size=6),
                st.sampled_from(["", ",", ".", "!", "?", ":", ";"]),
            ),
            min_size=1,
            max_size=8,
        ),
        separator=st.sampled_from([" ", "\t\n", "\u00a0", "\u2003"]),
        hops=st.tuples(st.integers(0, 20), st.integers(0, 60), st.integers(0, 20)),
        rest=st.integers(0, HOP - 1),
        loud_rest=st.booleans(),
        channels=st.integers(1, 2),
    )
    @example(  # a voiced span from 0.1 s to 0.9 s, its words weighed 2, 6 and 10
        words=["A", "bb,", "ccc."],
        separator=" ",
        hops=(10, 80, 10),
        rest=0,
        loud_rest=False,
        channels=1,
    )
    @example(  # audio shorter than a hop, voiced: none heard
        words=["one", "two"],
        separator=" ",
        hops=(0, 0, 0),
        rest=HOP - 1,
        loud_rest=True,
        channels=1,
    )
    def test_an_estimate_shares_the_voiced_span_by_letters_and_pauses(
        self,
        words: list[str],
        separator: str,
        hops: tuple[int, int, int],
        rest: int,
        loud_rest: bool,
        channels: int,
    ) -> None:
        """The audio is heard in hops of 10 ms; its words share the span of the hops heard (or
        all of it, if none is), each its letters and a pause after it: 6 letters' worth after
        a full stop (. ! ? : ;), 3 after a comma, 1 otherwise."""
        before, voiced, after = hops
        audio = np.zeros(((before + voiced + after) * HOP + rest, channels), np.float32)
        audio[before * HOP : (before + voiced) * HOP] = 0.1
        audio[len(audio) - rest :] = 0.1 if loud_rest else 0
        got = estimate(separator.join(words), audio)
        assert [w.text for w in got] == words
        if voiced:
            weights = [len(w) + PAUSES.get(w[-1], 1) for w in words]
            edges = np.cumsum([0, *weights]) / sum(weights)
            pauses = np.array(weights) - [len(w) for w in words]
            span = voiced / 100
            starts = before / 100 + edges[:-1] * span
            ends = before / 100 + (edges[1:] - pauses / sum(weights)) * span
        else:
            shares = np.arange(len(words) + 1) / len(words) * len(audio) / RATE
            starts, ends = shares[:-1], shares[1:]
        np.testing.assert_allclose([w.start for w in got], starts, atol=1e-12)
        np.testing.assert_allclose([w.end for w in got], ends, atol=1e-12)

    @pytest.mark.parametrize("kind", ["timed by its voice", "estimated"])
    @given(cut=st.floats(0, 1), factor=st.floats(0.25, 4))
    def test_words_move_with_trims_and_speed(
        self, kind: str, cut: float, factor: float
    ) -> None:
        text = "One two. Three four!"
        speech = (
            said(text)
            if kind == "timed by its voice"
            else Speech(np.full((RATE, 2), 0.1, np.float32), text=text, rate=RATE)
        )
        start = cut * speech.duration
        edited = speech.trim(start).speed(factor)
        kept = [w for w in speech.words if w.start >= start]
        assert [w.text for w in edited.words] == [w.text for w in kept]
        np.testing.assert_allclose(
            [(w.start, w.end) for w in edited.words],
            [((w.start - start) / factor, (w.end - start) / factor) for w in kept],
            atol=1e-12,
        )

    def test_a_trim_keeps_the_words_it_holds(self) -> None:
        speech = said("one two three")  # two starts at 0.2 s
        assert [w.text for w in speech.trim(0, 0.2).words] == ["one"]

    def test_captions_break_at_sentences(self) -> None:
        speech = said("One two. Three four five.")
        assert [text for _, _, text in lines(speech)] == [
            "One two.",
            "Three four five.",
        ]
