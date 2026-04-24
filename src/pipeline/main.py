import os
import librosa
import numpy as np

from .parser import save_to_json

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NUM_LANES = 4


def main(audio_path: str) -> dict:
    """
    Analyse un fichier audio et retourne les données de niveau au format Unity.

    Returns:
        {
            "meta": {"bpm": float, "key": str, "duration": float},
            "hits": [{"time": float, "lane": int, "type": str, "strength": float}],
            "sections": [{"start": float, "end": float, "label": str}]
        }
    """
    try:
        y, sr = librosa.load(audio_path)
    except Exception as exc:
        raise ValueError(f"Impossible de charger le fichier audio: {exc}") from exc

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo.item() if hasattr(tempo, "item") else tempo)
    beats = librosa.frames_to_time(beat_frames, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    beat_strengths = onset_env[beat_frames]

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    key = NOTES[int(np.argmax(chroma_mean))]

    duration = float(librosa.get_duration(y=y, sr=sr))

    hits = _beats_to_hits(beats, beat_strengths)
    sections = _build_sections(duration, tempo)

    return {
        "meta": {"bpm": round(tempo, 2), "key": key, "duration": round(duration, 3)},
        "hits": hits,
        "sections": sections,
    }


def _beats_to_hits(beats: np.ndarray, strengths: np.ndarray) -> list:
    if len(strengths) == 0:
        return []

    max_strength = float(np.max(strengths)) or 1.0
    hits = []

    for i, (timing, strength) in enumerate(zip(beats, strengths)):
        normalized = round(min(float(strength) / max_strength, 1.0), 3)
        hit_type = "hold" if normalized >= 0.85 else "tap"
        hits.append({
            "time": round(float(timing), 4),
            "lane": (i % NUM_LANES) + 1,
            "type": hit_type,
            "strength": normalized,
        })

    return hits


def _build_sections(duration: float, bpm: float) -> list:
    if bpm <= 0:
        return [{"start": 0.0, "end": round(duration, 3), "label": "main"}]

    beat_duration = 60.0 / bpm
    beats_per_bar = 4
    bar_duration = beat_duration * beats_per_bar
    bars_per_section = 16

    section_duration = bar_duration * bars_per_section
    labels = ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"]

    sections = []
    start = 0.0
    label_index = 0

    while start < duration:
        end = min(start + section_duration, duration)
        label = labels[label_index] if label_index < len(labels) else "chorus"
        sections.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "label": label,
        })
        start = end
        label_index += 1

    return sections


if __name__ == "__main__":
    os.makedirs("resultat", exist_ok=True)
    result = main("assets/Darude.mp3")
    save_to_json(
        "resultat/analyse_rythme.json",
        result["meta"]["key"],
        result["meta"]["bpm"],
        result["hits"],
        result["meta"]["duration"],
    )
    print("Données sauvegardées dans: resultat/analyse_rythme.json")
