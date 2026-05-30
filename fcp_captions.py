#!/usr/bin/env python3
"""
FCP Captions Generator
Generates Final Cut Pro XML (.fcpxml) with captions from audio using a local Whisper model.

Automatically manages a virtual environment and installs dependencies.
Settings are persisted in settings.json. Visual styling lives in style.json.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_DIR = SCRIPT_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python3"
SETTINGS_FILE = SCRIPT_DIR / "settings.json"
STYLE_FILE = SCRIPT_DIR / "style.json"


# ---------------------------------------------------------------------------
# Virtual environment bootstrap
# ---------------------------------------------------------------------------

def ensure_venv():
    """Create venv and install dependencies if needed, then re-exec inside it."""
    if sys.prefix == str(VENV_DIR):
        return

    if not VENV_PYTHON.exists():
        print("=== Setting up virtual environment ===")
        print(f"Creating venv in {VENV_DIR} ...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
        print("Installing openai-whisper (this may take a few minutes) ...")
        subprocess.check_call(
            [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
        )
        subprocess.check_call([str(VENV_PYTHON), "-m", "pip", "install", "openai-whisper"])
        print("Setup complete!\n")

    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__] + sys.argv[1:])


ensure_venv()

import whisper  # noqa: E402  (only reachable inside venv)


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "max_words": 10,
    "font_size": 18,
    "font": "Helvetica",
    "font_face": "Regular",
}

DEFAULT_STYLE = {
    # Vertical position offset in pixels (0 = centre of frame)
    "position_y": 0,

    # Output resolution
    "resolution": {
        "width": 1080,
        "height": 1920,
    },

    # Face / Stil  -----------------------------------------------------------
    "face": {
        "enabled": True,
        "color": "1.0 1.0 1.0",
        "opacity": 1.0,
    },

    # Stroke / Kontur  -------------------------------------------------------
    "stroke": {
        "enabled": True,
        "color": "0.0 0.0 0.0",
        "opacity": 1.0,
        "blur": 0,
        "width": 2,
    },

    # Drop Shadow / Schattenwurf  --------------------------------------------
    "shadow": {
        "enabled": True,
        "color": "0.0 0.0 0.0",
        "opacity": 1.0,
        "blur": 0,
        "distance": 0,
        "angle": 0,
    },
}


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """Load settings.json, falling back to defaults for missing keys."""
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**DEFAULT_SETTINGS, **saved}
            return merged
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {SETTINGS_FILE}, using defaults.")
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict):
    """Persist caption settings to settings.json."""
    keys = ["max_words", "font_size", "font", "font_face"]
    data = {k: settings[k] for k in keys if k in settings}
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_style() -> dict:
    """Load style.json, creating it with defaults if it doesn't exist."""
    if not STYLE_FILE.exists():
        STYLE_FILE.write_text(
            json.dumps(DEFAULT_STYLE, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Created default style config: {STYLE_FILE}")

    try:
        saved = json.loads(STYLE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Warning: Could not parse {STYLE_FILE}, using defaults.")
        return dict(DEFAULT_STYLE)

    # Backwards compat: legacy "font_color" RGBA string → face section
    if "font_color" in saved and "face" not in saved:
        parts = saved["font_color"].split()
        if len(parts) >= 3:
            opacity = float(parts[3]) if len(parts) >= 4 else 1.0
            saved["face"] = {
                "enabled": True,
                "color": " ".join(parts[:3]),
                "opacity": opacity,
            }

    # Deep-merge so new default keys survive manual deletions
    merged = dict(DEFAULT_STYLE)
    merged.update(saved)
    for section in ("face", "stroke", "shadow", "resolution"):
        merged[section] = {**DEFAULT_STYLE[section], **saved.get(section, {})}
    return merged


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def find_whisper_models():
    cache_dir = Path.home() / ".cache" / "whisper"
    if not cache_dir.is_dir():
        return []
    return sorted((f.stem, f) for f in cache_dir.iterdir() if f.suffix == ".pt")


def select_model_interactive():
    available = find_whisper_models()

    print("\n=== Whisper Model Selection ===")
    print("1) Auto-detect installed models")
    print("2) Specify model path manually")
    print("3) Download a model")
    choice = input("\nChoice [1]: ").strip() or "1"

    if choice == "1":
        if not available:
            print("No models found in ~/.cache/whisper/ – falling back to download...")
            return select_model_download()
        print("\nFound models:")
        for i, (name, path) in enumerate(available, 1):
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  {i}) {name} ({size_mb:.0f} MB)")
        idx = input("\nSelect model [1]: ").strip() or "1"
        try:
            return available[int(idx) - 1][0]
        except (ValueError, IndexError):
            return available[0][0]

    elif choice == "2":
        path = input("Model path: ").strip()
        if not os.path.isfile(path):
            print(f"Error: File not found: {path}")
            sys.exit(1)
        return path

    elif choice == "3":
        return select_model_download()

    print("Invalid choice.")
    sys.exit(1)


def select_model_download():
    sizes = ["tiny", "base", "small", "medium", "large"]
    print("\nAvailable models to download:")
    for i, name in enumerate(sizes, 1):
        print(f"  {i}) {name}")
    idx = input("\nSelect model [2 (base)]: ").strip() or "2"
    try:
        model_name = sizes[int(idx) - 1]
    except (ValueError, IndexError):
        model_name = "base"

    print(f"\nDownloading model '{model_name}' ...")
    whisper.load_model(model_name)
    print("Download complete!")
    return model_name


def select_language():
    print("\n=== Language Selection ===")
    print("1) Auto-detect")
    print("2) German (de)")
    print("3) English (en)")
    print("4) Other (enter code)")
    choice = input("\nChoice [1]: ").strip() or "1"

    if choice == "2":
        return "de"
    if choice == "3":
        return "en"
    if choice == "4":
        code = input("Language code (e.g. fr, es, it): ").strip()
        return code or None
    return None


def configure_captions(saved: dict) -> dict:
    """Interactive caption settings, showing saved values as defaults."""
    print("\n=== Caption Settings ===")

    def ask(prompt, key, cast=str):
        default = saved.get(key, DEFAULT_SETTINGS[key])
        raw = input(f"{prompt} [{default}]: ").strip()
        return cast(raw) if raw else cast(default)

    max_words = ask("Max words per caption", "max_words", int)
    font_size  = ask("Font size", "font_size", int)
    font       = ask("Font name", "font")
    font_face  = ask("Font face (Regular/Bold)", "font_face")

    return {
        "max_words": max_words,
        "font_size": font_size,
        "font": font,
        "font_face": font_face,
        "bold": font_face.lower() == "bold",
    }


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe_audio(audio_path, model_name, language=None):
    print(f"\nLoading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)
    print(f"Transcribing '{audio_path}'...")
    options = {"word_timestamps": True}
    if language:
        options["language"] = language
    result = model.transcribe(audio_path, **options)
    print(f"Detected language: {result.get('language', 'unknown')}")
    return result


def split_segments_by_word_count(result, max_words):
    captions = []
    for segment in result["segments"]:
        words = segment.get("words", [])
        if not words:
            captions.append({
                "text": segment["text"].strip(),
                "start": segment["start"],
                "end": segment["end"],
            })
            continue
        for i in range(0, len(words), max_words):
            chunk = words[i:i + max_words]
            text = "".join(w["word"] for w in chunk).strip()
            if text:
                captions.append({"text": text, "start": chunk[0]["start"], "end": chunk[-1]["end"]})
    return captions


# ---------------------------------------------------------------------------
# FCPXML generation
# ---------------------------------------------------------------------------

def seconds_to_frames(seconds, fps=30):
    return round(seconds * fps)


def _xml_escape(text):
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _fmt_num(n) -> str:
    """Compact numeric formatting: drop trailing zeros (1.0 → '1', 0.75 → '0.75')."""
    if isinstance(n, int):
        return str(n)
    if float(n).is_integer():
        return str(int(n))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def _rgba(rgb_str: str, opacity: float) -> str:
    """Combine 'R G B' string + opacity float into 'R G B A' FCPXML value (compact format)."""
    rgb = " ".join(_fmt_num(float(c)) for c in rgb_str.split())
    return f"{rgb} {_fmt_num(opacity)}"


def build_style_attrs(settings: dict, style: dict) -> str:
    """Build the text-style XML attribute string from settings + style config."""
    face = style.get("face", DEFAULT_STYLE["face"])
    face_opacity = face.get("opacity", 1.0) if face.get("enabled", True) else 0.0
    face_color = _rgba(face.get("color", "1.0 1.0 1.0"), face_opacity)

    attrs = (
        f'font="{_xml_escape(settings["font"])}" '
        f'fontSize="{settings["font_size"]}" '
        f'fontFace="{settings["font_face"]}" '
        f'fontColor="{face_color}"'
    )

    stroke = style.get("stroke", {})
    if stroke.get("enabled", False):
        color = _rgba(stroke["color"], stroke.get("opacity", 1.0))
        # strokeWidth must be NEGATIVE: that draws the outline outside the glyph
        # so the face fill stays visible. A positive value strokes inward and
        # paints over the fill, making the text appear to have no fill at all.
        stroke_width = -abs(stroke.get("width", 2))
        attrs += (
            f' bold="1"'
            f' strokeColor="{color}"'
            f' strokeWidth="{_fmt_num(stroke_width)}"'
        )

    shadow = style.get("shadow", {})
    if shadow.get("enabled", True):
        color = _rgba(shadow["color"], shadow.get("opacity", 0.75))
        attrs += f' shadowColor="{color}"'
        distance = shadow.get("distance", 4)
        angle = shadow.get("angle", 315)
        if distance or angle:
            attrs += f' shadowOffset="{distance} {angle}"'
        blur = shadow.get("blur", 0)
        if blur:
            attrs += f' shadowBlurRadius="{blur}"'

    attrs += ' alignment="center"'
    return attrs


def build_title_params(style: dict, indent: str) -> list[str]:
    """Build the <param> elements that go inside <title> (above <text>)."""
    lines = [
        f'{indent}<param name="Flatten" '
        f'key="9999/999166631/999166633/2/351" value="1"></param>',
        f'{indent}<param name="Alignment" '
        f'key="9999/999166631/999166633/2/354/999169573/401" value="1 (Center)"></param>',
    ]

    # Face / Stil — FCP only renders the face when these explicit params are present.
    # Without them the Stil checkbox imports as off and the text fill is invisible.
    face = style.get("face", DEFAULT_STYLE["face"])
    if face.get("enabled", True):
        face_rgb = " ".join(_fmt_num(float(c)) for c in face.get("color", "1 1 1").split())
        lines += [
            f'{indent}<param name="Farbe" '
            f'key="9999/999166631/999166633/5/999166635/14/16" value="{face_rgb}"></param>',
            f'{indent}<param name="Randmodus" '
            f'key="9999/999166631/999166633/5/999166635/14/18/5" value="1 (Wiederholen)"></param>',
        ]

    stroke = style.get("stroke", {})
    if stroke.get("enabled", False):
        blur = stroke.get("blur", 0)
        if blur:
            lines.append(
                f'{indent}<param name="Weichzeichnen" '
                f'key="9999/999166631/999166633/5/999166635/30/76" '
                f'value="{blur} {blur}"></param>'
            )

    lines.append(f'{indent}<param name="disableDRT" key="3733" value="1"></param>')
    return lines


def _format_name(width: int, height: int) -> str:
    """Derive the FCP format string from pixel dimensions."""
    return f"FFVideoFormat{width}x{height}p3000" if width != height else f"FFVideoFormat{width}p3000"


def generate_fcpxml(captions, settings, style, project_name):
    frame_duration = "100/3000s"
    total_seconds = (captions[-1]["end"] + 1) if captions else 1
    total_frames = seconds_to_frames(total_seconds)
    gap_frames = total_frames * 100
    pos_y = style.get("position_y", 0)

    res = style.get("resolution", DEFAULT_STYLE["resolution"])
    width, height = res["width"], res["height"]
    fmt_name = _format_name(width, height)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE fcpxml>',
        '',
        '<fcpxml version="1.14">',
        '    <resources>',
        f'        <format id="r1" name="{fmt_name}" '
        f'frameDuration="{frame_duration}" '
        f'width="{width}" height="{height}" '
        f'colorSpace="1-1-1 (Rec. 709)"></format>',
        '        <effect id="r2" name="Basic Title" '
        'uid=".../Titles.localized/Bumper:Opener.localized/'
        'Basic Title.localized/Basic Title.moti"></effect>',
        '    </resources>',
        '    <library>',
        '        <event name="Auto generated Captions">',
        f'            <project name="{_xml_escape(project_name)}">',
        f'                <sequence format="r1" tcStart="0s" tcFormat="NDF" '
        f'audioLayout="stereo" audioRate="48k" '
        f'duration="{total_frames * 100}/3000s">',
        '                    <spine>',
        f'                        <gap name="Gap" offset="0s" duration="{gap_frames}/3000s">',
        '                            <spine lane="1" offset="0s">',
    ]

    style_attrs = build_style_attrs(settings, style)
    title_indent = ' ' * 36
    title_params = build_title_params(style, title_indent)

    prev_end = 0
    for i, cap in enumerate(captions):
        offset_frames = seconds_to_frames(cap["start"]) * 100
        duration_frames = max(seconds_to_frames(cap["end"] - cap["start"]), 1) * 100

        # Frame-rounding can place a caption's start 1 frame before the previous
        # caption's end. Inside a single connected storyline clips must be strictly
        # sequential — an overlap makes FCP drop the real title and substitute an
        # empty "Titel" placeholder. Clamp the start so titles never overlap.
        if offset_frames < prev_end:
            offset_frames = prev_end

        # Insert a connected-storyline gap clip when there's space between titles.
        # FCP needs the inner spine to be a contiguous timeline; without explicit
        # Lücke clips the imported titles get incomplete state (Stil toggle off).
        if offset_frames > prev_end:
            lines.append(
                f'                                <gap name="Lücke" '
                f'offset="{prev_end}/3000s" start="3600s" '
                f'duration="{offset_frames - prev_end}/3000s"></gap>'
            )

        ts_id = f"ts{i}"
        title_name = _xml_escape(f'{cap["text"]} - Basic Title')
        text = _xml_escape(cap["text"])

        lines.append(
            f'                                <title ref="r2" '
            f'offset="{offset_frames}/3000s" '
            f'name="{title_name}" '
            f'start="100/3000s" duration="{duration_frames}/3000s">'
        )
        lines.extend(title_params)
        lines += [
            f'{title_indent}<text>',
            f'{title_indent}    <text-style ref="{ts_id}">{text}</text-style>',
            f'{title_indent}</text>',
            f'{title_indent}<text-style-def id="{ts_id}">',
            f'{title_indent}    <text-style {style_attrs}></text-style>',
            f'{title_indent}</text-style-def>',
        ]
        if pos_y:
            lines.append(f'{title_indent}<adjust-transform position="0 {pos_y}"></adjust-transform>')
        lines.append('                                </title>')

        prev_end = offset_frames + duration_frames

    lines += [
        '                            </spine>',
        '                        </gap>',
        '                    </spine>',
        '                </sequence>',
        '            </project>',
        '        </event>',
        '    </library>',
        '</fcpxml>',
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate Final Cut Pro XML captions from audio using Whisper"
    )
    parser.add_argument("audio", nargs="?", help="Path to audio file")
    parser.add_argument("-m", "--model", help="Whisper model name or path")
    parser.add_argument("-l", "--language", help="Language code (e.g. de, en) or 'auto'")
    parser.add_argument("-w", "--max-words", type=int, help="Max words per caption")
    parser.add_argument("-s", "--font-size", type=int, help="Font size")
    parser.add_argument("-f", "--font", help="Font name")
    parser.add_argument("--font-face", help="Font face (Regular/Bold)")
    parser.add_argument("-o", "--output", help="Output .fcpxml file path")
    args = parser.parse_args()

    print("=== FCP Captions Generator ===")

    # Load persisted settings and style config
    saved_settings = load_settings()
    style = load_style()

    # Audio file
    audio_path = args.audio
    if not audio_path:
        audio_path = input("\nPath to audio file: ").strip()
    if not os.path.isfile(audio_path):
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)

    # Model
    model_name = args.model or select_model_interactive()

    # Language
    if args.language:
        language = None if args.language == "auto" else args.language
    else:
        language = select_language()

    # Caption settings – CLI args override saved, saved override defaults
    if any([args.max_words, args.font_size, args.font, args.font_face]):
        font_face = args.font_face or saved_settings["font_face"]
        settings = {
            "max_words": args.max_words or saved_settings["max_words"],
            "font_size": args.font_size or saved_settings["font_size"],
            "font": args.font or saved_settings["font"],
            "font_face": font_face,
            "bold": font_face.lower() == "bold",
        }
    else:
        settings = configure_captions(saved_settings)

    # Persist settings for next run
    save_settings(settings)

    # Transcribe
    result = transcribe_audio(audio_path, model_name, language)

    captions = split_segments_by_word_count(result, settings["max_words"])
    print(f"\nGenerated {len(captions)} caption segments.")

    project_name = Path(audio_path).stem + "_captions"
    fcpxml = generate_fcpxml(captions, settings, style, project_name)

    output_path = args.output or (os.path.splitext(audio_path)[0] + "_captions.fcpxml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(fcpxml)

    print(f"\nFCPXML saved to: {output_path}")
    print("Import this file into Final Cut Pro to use the captions.")


if __name__ == "__main__":
    main()
