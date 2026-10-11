"""ManimGX's engine (Rust): typesets Typst documents, and draws a film's frames on the GPU and
encodes them into an MP4.

Shapes, brushes and images are uploaded once, under a nonzero key; a frame is then a view (48
float32: projection, overlay, pixels, light, toward; then the background) and one 336-byte record
per object (see `manimgx.rendering.feed`). A document is typeset in this process by Typst as a library, and
its layout read off Typst's frames (see `manimgx.drawing.typesetting`).
"""

from collections.abc import Sequence
from pathlib import Path

DEFAULT_ENCODER_PRESET: str
DEFAULT_ENCODER_CRF: float

TAKE_VERSION: int
"""The take format written by Recorder and supported by Replay and the native/browser player."""

# a camera's view, drawn into a texture that later views sample by its key:
# (key, width, height, view, records)
type CameraView = tuple[int, int, int, bytes, bytes]

class Player:
    """The GPU's player (natively only: in Pyodide the engine has no GPU, and a film records a
    take instead, with `Recorder`)."""

    def __init__(self, width: int, height: int, samples: int = 4) -> None: ...
    def add_path(
        self, key: int, points: bytes, subpaths: bytes, centroid_area: Sequence[float]
    ) -> None:
        """A path: its control points (float64 x, y, z; four per curve), its subpaths (uint32
        first curve, end curve, closed, 0) and (centroid, Newell area vector) of its control
        points."""

    def add_points(self, key: int, vertices: bytes) -> None: ...
    def add_mesh(
        self,
        key: int,
        points: bytes,
        uvs: bytes,
        normals: bytes,
        triangles: bytes,
        outline: int = 0,
        block: int = 0,
    ) -> None:
        """A mesh as its object defines it: its points and texture coordinates (float64 x, y, z
        and u, v), its triangles (uint32, three each) and its normals (float64) when its geometry
        gives them, or empty: each vertex's is then the area-weighted sum of its faces'.
        `outline` > 2: the vertices are faces — blocks of `block` (by default `outline`), each
        beginning with a closed loop of `outline` — stroked."""

    def add_rows(self, key: int, rows: bytes) -> None: ...
    def add_texture(self, key: int, width: int, height: int, rgba: bytes) -> None: ...
    def add_environment(self, id: int, width: int, height: int, rgbe: bytes) -> None:
        """An environment's picture (equirectangular RGBE rows, top to bottom), named `id` by
        the views whose lights show it (kept as long as the player; 0 is the built-in
        studio, which the player makes); its sun, if it has one, is lifted out of it into a
        sun the views light by."""

    def grow_path(self, key: int, points: bytes, closed: bool = False) -> None:
        """Append curves (float64 control points, four per curve) to a path's last subpath;
        `closed`: whether it now ends where it begins."""

    def evict(self, keys: Sequence[int]) -> None:
        """Forget shapes, brushes and textures no frame shows any more."""

    def stored(self) -> tuple[int, int]:
        """(bytes in the store's arrays, of which dead): what the arrays sent to the GPU hold."""

    def pressured(self) -> bool:
        """Whether the resident arrays exceed a GPU buffer's capacity; brings up the GPU."""

    def render(
        self, view: bytes, records: bytes, cameras: Sequence[CameraView] = ...
    ) -> bytes:
        """One frame, read back: RGBA8 rows, top to bottom."""

    def begin_export(
        self,
        path: str,
        fps: int = 60,
        preset: str = ...,
        crf: float = ...,
        options: Sequence[tuple[str, str]] = ...,
    ) -> None:
        """Start an MP4 at `path` (x264 at `preset` and `crf`, `options` its own settings)."""

    def push(
        self,
        view: bytes,
        records: bytes,
        repeat: int = 1,
        cameras: Sequence[CameraView] = ...,
        key: bool = False,
        capture: bool = False,
    ) -> bytes | None:
        """The next frame of the video, shown for `repeat` frames; `key`: a keyframe, where a
        player can start (a section's first frame). With `capture`, return the same draw's
        full-quality RGBA8 pixels, waiting for any overflow retries."""

    def abort_export(self) -> None:
        """Abandon the video: nothing is written."""

    def end_export(
        self,
        sound: bytes | None = None,
        channels: int = 1,
        rate: int = 48000,
        bitrate: int = 192000,
    ) -> tuple[float, float, float, int]:
        """Finish the video, with `sound` beside it if given: float32 samples, interleaved,
        `channels` of them, at `rate` samples a second, encoded as AAC-LC at about `bitrate`
        bits a second. Returns (seconds, of which in x264, share of macroblocks converted,
        bytes)."""

class Replay:
    """One complete, successful take, using the native player's decoder and renderer."""

    def __init__(self, data: bytes) -> None: ...
    @property
    def size(self) -> tuple[int, int]:
        """The recorded width and height, in pixels."""

    @property
    def frames(self) -> int:
        """The frame count, including repeated frames."""

    @property
    def fps(self) -> float: ...
    @property
    def timeline(self) -> list[tuple[int, int]]:
        """Each recorded shot's first frame and repeat count."""

    def render(self, frame: int) -> bytes:
        """A zero-based frame, in any order, as RGBA8 bytes; out-of-range indices fail."""

def start_gpu() -> bool:
    """Start bringing the GPU up, on a thread of its own, unless that has begun; whether this
    call began it (natively only). What draws first waits for it, and so does Python as it
    exits. A process that will draw calls it as early as it knows; one that never draws never
    brings the GPU up."""

def adapter_info() -> dict[str, str]:
    """The active GPU's name, vendor, device, device_type, driver, driver_info and backend.

    Brings the GPU up if necessary; available in the native engine.
    """

def decode_audio(data: bytes, rate: int) -> tuple[bytes, int]:
    """A file's audio (its bytes, any container and codec the engine's FFmpeg decodes: WAV,
    AIFF, CAF, MP3, AAC, Opus, Vorbis, FLAC, ALAC; in MP4, MOV, WebM, Matroska) at `rate` samples
    a second, starting and ending where the file declares: float32 samples, interleaved, and how
    many channels (1 or 2: wider sound is mixed down to stereo)."""

def resample_audio(samples: bytes, channels: int, rate: float, to: float) -> bytes:
    """Interleaved float32 samples of `channels` channels at `rate` samples a second,
    resampled to `to`."""

def read_hdr(data: bytes) -> tuple[int, int, bytes]:
    """A Radiance (.hdr) file's picture (its bytes) as an environment keeps it: its width,
    height, and RGBE pixels row by row from the top, halved until no wider than 4096."""

class Recorder:
    """A take being recorded: the engine's calls — the same uploads a player takes, then frames —
    written as the stream ManimGX's player (in a window, or a page) plays back. It
    draws nothing."""

    def __init__(self, width: int, height: int, fps: float) -> None: ...
    def add_path(
        self, key: int, points: bytes, subpaths: bytes, centroid_area: Sequence[float]
    ) -> None: ...
    def add_points(self, key: int, vertices: bytes) -> None: ...
    def add_mesh(
        self,
        key: int,
        points: bytes,
        uvs: bytes,
        normals: bytes,
        triangles: bytes,
        outline: int = 0,
        block: int = 0,
    ) -> None: ...
    def add_rows(self, key: int, rows: bytes) -> None: ...
    def add_texture(self, key: int, width: int, height: int, rgba: bytes) -> None: ...
    def add_environment(
        self, id: int, width: int, height: int, rgbe: bytes
    ) -> None: ...
    def grow_path(self, key: int, points: bytes, closed: bool = False) -> None: ...
    def evict(self, keys: Sequence[int]) -> None: ...
    def stored(self) -> tuple[int, int]:
        """(0, 0): a take holds nothing on a GPU."""

    def frame(
        self,
        view: bytes,
        records: bytes,
        repeat: int = 1,
        cameras: Sequence[CameraView] = ...,
    ) -> None:
        """The next frame, shown for `repeat` frames (as a player's `push`)."""

    def note(self, json: str) -> None:
        """A note for whoever shows the take (JSON: a play that ended, a section, the
        captions)."""

    def sound(self, file: bytes) -> None:
        """The film's sound: an audio file, which the player plays beside the frames."""

    def end(self, failed: bool = False) -> None:
        """The take's end: its film ended, or (`failed`) its scene failed."""

    def drain(self) -> bytes:
        """What has been recorded since the last drain."""

def note(json: str) -> bytes:
    """A note on its own: a message of the take's stream that belongs to no take (the file's
    scenes, an error)."""

def web() -> tuple[str, bytes] | None:
    """The player for a page, this engine built for the browser: wasm-bindgen's JS and the
    WebAssembly it loads, which Pyodide's engine carries; None in any other (natively, a film
    plays in a window: `window`), or one built without it (no wasm32-unknown-unknown target).
    """

def window(title: str, time: float = 0.0, fonts: Sequence[str] = ...) -> None:
    """Open ManimGX's player in a window on this machine's screen, playing the takes that come
    on standard input, until the window is closed or its input ends. It starts at `time`
    seconds; its text is set in the fonts under `fonts`. Natively only."""

def digest(*parts: bytes) -> int:
    """The content key of the parts' bytes, taken as one stream (xxh3, 64 bits, never 0): what
    names an upload, so that equal content is uploaded once."""

class TypstError(Exception):
    """Typst could not typeset a document (its errors, joined)."""

def cache_directory() -> Path | None:
    """The current user's cache root, or the browser's private filesystem; None disables it."""

def typeset(
    source: str,
    font_paths: Sequence[str],
    packages: str | None = None,
    *,
    revision: int = 0,
) -> tuple[bytes, list[bytes], list[tuple[str, list[int]]], bool]:
    """Typeset `source` (Typst): its items as float64 rows of 23 (kind, key, placement a b c d e f,
    fill rgba, stroke rgba, stroke width, advance, node start, end, drawn start, end, node kind),
    its shapes' cubic points (float64 x y z), its labelled groups (a label and the items inside
    it) and whether it needed the system's fonts. `revision` identifies the caller's font and
    package dependencies; a changed revision replaces the setup remembered for those paths."""

def glyph_outlines(keys: Sequence[int]) -> list[bytes]:
    """Each key's outline as cubic points (float64 x y z, font units, y up); empty: blank."""

def ligature_carets(key: int) -> list[float]:
    """A ligature glyph's carets from its font (font units); empty: the font gives none."""

def graphemes(text: str) -> list[int]:
    """Where `text`'s graphemes start, in characters."""

def mitex_math(latex: str) -> str:
    """LaTeX math as Typst math (mitex); raises TypstError on what it can't convert."""

def mitex_text(latex: str) -> str:
    """LaTeX text as Typst markup (mitex); raises TypstError on what it can't convert."""

def system_fonts_fingerprint() -> int:
    """The system's fonts' fingerprint (their files' paths, sizes and times), once per process."""

def face_fonts(dirs: Sequence[str]) -> list[bytes]:
    """The fonts a player's face is set in: the font files in `dirs` (ManimGX's), and Typst's
    monospace one (DejaVu Sans Mono), each file's bytes."""
