import io
import wave
import struct
import logging
from abc import ABC, abstractmethod
from typing import Optional
from config import settings
from services.voice.models import GeneratedAudio, TtsOptions

logger = logging.getLogger("tts_provider")


class PersianTtsProvider(ABC):
    """
    Abstract Base Class for Persian Text-To-Speech providers.
    Generates synthetic or cloud-synthesized audio from Persian text.
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        options: Optional[TtsOptions] = None
    ) -> GeneratedAudio:
        """
        Synthesize Persian text to speech.
        Returns: GeneratedAudio containing audio bytes and format metadata.
        """
        pass


class MockPersianTtsProvider(PersianTtsProvider):
    """
    In-memory Mock Persian TTS provider for unit tests and local development.
    Generates valid standard RIFF WAV bytes with a silent PCM track of calculated duration,
    avoiding real network requests while validating media formatting and playback compatibility.
    """

    async def synthesize(
        self,
        text: str,
        options: Optional[TtsOptions] = None
    ) -> GeneratedAudio:
        opts = options or TtsOptions()
        sample_rate = opts.sample_rate or 16000

        # Estimate duration based on Persian word count (~3 words per second)
        word_count = max(1, len(text.split()))
        duration_seconds = max(1.5, round(word_count / 3.0, 2))

        # Generate a valid 16-bit Mono PCM WAV buffer
        num_samples = int(sample_rate * duration_seconds)
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            # Silent PCM frames
            silent_frames = struct.pack(f"<{num_samples}h", *(0 for _ in range(num_samples)))
            wav_file.writeframes(silent_frames)

        audio_bytes = wav_io.getvalue()
        logger.info(
            f"[MOCK TTS] Synthesized {len(audio_bytes)} bytes WAV audio for Persian text: "
            f"'{text[:40]}...' (estimated duration: {duration_seconds}s)"
        )

        return GeneratedAudio(
            audio_content=audio_bytes,
            format="wav",
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            text=text
        )


class PoshteyarAnnouncementTtsProvider(PersianTtsProvider):
    """
    Poshteyar Native Persian TTS Provider.
    Poshteyar's outbound engine integrates Persian Gemini Flash Lite TTS natively
    when outbound_type is 'announcement', passing the text directly to the telephony engine.
    """

    async def synthesize(
        self,
        text: str,
        options: Optional[TtsOptions] = None
    ) -> GeneratedAudio:
        opts = options or TtsOptions()
        word_count = max(1, len(text.split()))
        duration_seconds = max(2.0, round(word_count / 2.8, 2))

        logger.info(f"[POSHTYAR TTS] Prepared Persian announcement text for Poshteyar engine ({len(text)} chars)")
        return GeneratedAudio(
            audio_content=text.encode("utf-8"),
            format="poshteyar_announcement",
            duration_seconds=duration_seconds,
            sample_rate=16000,
            text=text
        )


class GooglePersianTtsProvider(PersianTtsProvider):
    """
    Persian TTS adapter utilizing gTTS (Google Text-to-Speech) for Persian (fa-IR).
    Falls back gracefully to Mock if gTTS is unavailable or network is disconnected.
    """

    async def synthesize(
        self,
        text: str,
        options: Optional[TtsOptions] = None
    ) -> GeneratedAudio:
        opts = options or TtsOptions()
        try:
            from gtts import gTTS
            mp3_fp = io.BytesIO()
            tts = gTTS(text=text, lang="fa", slow=False)
            tts.write_to_fp(mp3_fp)
            audio_bytes = mp3_fp.getvalue()
            word_count = max(1, len(text.split()))
            duration_seconds = max(2.0, round(word_count / 3.0, 2))

            logger.info(f"[GOOGLE TTS] Synthesized {len(audio_bytes)} bytes MP3 audio for Persian text")
            return GeneratedAudio(
                audio_content=audio_bytes,
                format="mp3",
                duration_seconds=duration_seconds,
                sample_rate=24000,
                text=text
            )
        except Exception as e:
            logger.warning(f"gTTS invocation failed or not installed ({e}); falling back to MockPersianTtsProvider.")
            fallback = MockPersianTtsProvider()
            return await fallback.synthesize(text, options)


def get_tts_provider(provider_name: Optional[str] = None) -> PersianTtsProvider:
    """Factory to retrieve configured Persian TTS Provider."""
    chosen = (provider_name or settings.TTS_PROVIDER).lower()
    if chosen == "poshteyar":
        return PoshteyarAnnouncementTtsProvider()
    elif chosen == "gtts":
        return GooglePersianTtsProvider()
    else:
        return MockPersianTtsProvider()
