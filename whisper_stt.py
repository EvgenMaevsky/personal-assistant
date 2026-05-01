import os
import subprocess
import tempfile
from config import config

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(config.whisper_model, device="cpu", compute_type="int8")
    return _model


def transcribe(ogg_bytes: bytes) -> str:
    """Transcribe OGA voice bytes to text. Raises subprocess.CalledProcessError if ffmpeg fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        oga_path = os.path.join(tmpdir, "audio.oga")
        wav_path = os.path.join(tmpdir, "audio.wav")
        with open(oga_path, "wb") as f:
            f.write(ogg_bytes)
        subprocess.run(
            ["ffmpeg", "-i", oga_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            capture_output=True,
        )
        model = _get_model()
        segments, _ = model.transcribe(wav_path, language="uk")
        return " ".join(seg.text.strip() for seg in segments).strip()
