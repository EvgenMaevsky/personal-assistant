# tests/test_whisper_stt.py
import subprocess
import pytest
from unittest.mock import MagicMock, patch


@patch("whisper_stt.subprocess.run")
@patch("whisper_stt._get_model")
def test_transcribe_returns_joined_text(mock_get_model, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    seg1 = MagicMock()
    seg1.text = " нагадай"
    seg2 = MagicMock()
    seg2.text = " про зустріч "
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([seg1, seg2], MagicMock())
    mock_get_model.return_value = mock_model

    from whisper_stt import transcribe
    result = transcribe(b"fake_audio")
    assert result == "нагадай про зустріч"


@patch("whisper_stt.subprocess.run")
def test_transcribe_raises_on_ffmpeg_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr=b"error")

    from whisper_stt import transcribe
    with pytest.raises(subprocess.CalledProcessError):
        transcribe(b"bad_audio")


@patch("whisper_stt.subprocess.run")
@patch("whisper_stt._get_model")
def test_transcribe_strips_whitespace(mock_get_model, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    seg = MagicMock()
    seg.text = "  текст  "
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([seg], MagicMock())
    mock_get_model.return_value = mock_model

    from whisper_stt import transcribe
    result = transcribe(b"audio")
    assert result == "текст"
