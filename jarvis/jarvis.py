#!/usr/bin/env python3
"""
Jarvis — Assistente vocale per pi agent (Windows)
==================================================
Loop principale: ascolta -> trascrive -> interroga pi -> risponde a voce.
Architettura: sounddevice -> webrtcvad -> faster-whisper (IT) -> pi RPC -> edge-tts
Modalita: --mode wakeword (default) o --mode ptt
"""

from __future__ import annotations
import argparse, asyncio, json, logging, os, queue, subprocess, sys
import tempfile, threading, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import sounddevice as sd

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "config.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    RAW_CFG = json.load(f)


@dataclass
class Config:
    mode: str = RAW_CFG.get("mode", "wakeword")
    whisper_model: str = RAW_CFG["whisper"]["model"]
    whisper_lang: str = RAW_CFG["whisper"]["language"]
    whisper_device: str = RAW_CFG["whisper"]["device"]
    whisper_compute: str = RAW_CFG["whisper"]["compute_type"]
    vad_enabled: bool = RAW_CFG["vad"]["enabled"]
    vad_aggressiveness: int = RAW_CFG["vad"].get("aggressiveness", 1)
    tts_engine: str = RAW_CFG["tts"]["engine"]
    tts_voice: str = RAW_CFG["tts"]["voice"]
    tts_rate: str = RAW_CFG["tts"].get("rate", "+0%")
    tts_volume: str = RAW_CFG["tts"].get("volume", "+0%")
    pi_cwd: str = RAW_CFG["pi"]["cwd"]
    pi_no_session: bool = RAW_CFG["pi"].get("no_session", False)
    pi_session_dir: str = RAW_CFG["pi"].get("session_dir", str(HERE / ".pi-sessions"))
    pi_provider: str = RAW_CFG["pi"].get("provider", "")
    pi_model: str = RAW_CFG["pi"].get("model", "openrouter/free")
    pi_thinking: str = RAW_CFG["pi"].get("thinking", "off")
    ww_sensitivity: float = RAW_CFG["wakeword"]["sensitivity"]
    ptt_silence_timeout: float = RAW_CFG["ptt"]["silence_timeout"]
    ptt_min_phrase: float = RAW_CFG["ptt"]["min_phrase_seconds"]
    audio_sr: int = RAW_CFG["audio"]["sample_rate"]
    audio_channels: int = RAW_CFG["audio"]["channels"]
    audio_blocksize: int = RAW_CFG["audio"]["blocksize"]
    audio_device: Optional[int] = RAW_CFG["audio"]["device"]

    def pi_args(self) -> list[str]:
        pi_bin = "pi.cmd" if sys.platform == "win32" else "pi"
        # --no-session per startup veloce (nessun caricamento sessione)
        args = [pi_bin, "--mode", "rpc", "--no-session"]
        if self.pi_provider:
            args.extend(["--provider", self.pi_provider])
        if self.pi_model:
            args.extend(["--model", self.pi_model])
        if self.pi_thinking and self.pi_thinking != "off":
            args.extend(["--thinking", self.pi_thinking])
        # -ne evita conflitti tra estensioni
        args.append("-ne")
        return args


CFG = Config()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("jarvis")


# ================================================================
# Pi RPC Client
# ================================================================

class PiRPCClient:
    """Gestisce la connessione RPC a pi agent in un processo separato."""

    def __init__(self, config: Config):
        self.config = config
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._response_queue: queue.Queue[dict] = queue.Queue()
        self._event_callbacks: list[callable] = []
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._session_ready = threading.Event()
        self._full_response: list[str] = []

    def start(self):
        if self._proc is not None:
            return
        env = os.environ.copy()
        cmd = self.config.pi_args()
        log.info(f"Avvio pi RPC: {' '.join(cmd)}")
        log.info(f"  cwd={self.config.pi_cwd}")
        if self.config.pi_session_dir and not self.config.pi_no_session:
            os.makedirs(self.config.pi_session_dir, exist_ok=True)
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, cwd=self.config.pi_cwd,
            env=env, bufsize=1,
        )
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="pi-reader"
        )
        self._reader_thread.start()
        ready = self._session_ready.wait(timeout=15)
        if not ready:
            log.warning("pi RPC non risponde — continuo lo stesso")
        else:
            log.info("pi RPC pronto")

    def _reader_loop(self):
        assert self._proc is not None and self._proc.stdout is not None
        first_event = True
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                log.warning(f"JSON non valido da pi: {line[:120]}")
                continue
            if first_event:
                first_event = False
                self._session_ready.set()
            ev_type = event.get("type")
            if ev_type == "response":
                self._response_queue.put(event)
                continue
            if ev_type == "message_update":
                delta = event.get("assistantMessageEvent", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("delta", "")
                    self._full_response.append(text)
                    for cb in self._event_callbacks:
                        cb("text_delta", text)
            if ev_type == "tool_execution_start":
                for cb in self._event_callbacks:
                    cb("tool_start", event.get("toolName", ""))
            if ev_type == "tool_execution_end":
                for cb in self._event_callbacks:
                    cb("tool_end", event.get("toolName", ""))
            if ev_type == "agent_end":
                for cb in self._event_callbacks:
                    cb("agent_end", None)
            if ev_type == "agent_settled":
                full = "".join(self._full_response)
                self._full_response.clear()
                for cb in self._event_callbacks:
                    cb("agent_settled", full)
            if ev_type == "error":
                log.error(f"Errore da pi: {event.get('error', 'unknown')}")
        self._running = False
        log.warning("pi RPC connessione persa")

    def send(self, command: dict) -> Optional[dict]:
        assert self._proc is not None and self._proc.stdin is not None
        with self._lock:
            line = json.dumps(command, ensure_ascii=False) + "\n"
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
        timeout = 60
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = self._response_queue.get(timeout=0.5)
                return resp
            except queue.Empty:
                if not self._running:
                    return None
                continue
        log.warning("Timeout in attesa di risposta da pi")
        return None

    def prompt(self, text: str) -> bool:
        self._full_response.clear()
        resp = self.send({"type": "prompt", "message": text})
        if resp is None:
            return False
        return resp.get("success", False)

    def add_event_callback(self, callback: callable):
        self._event_callbacks.append(callback)

    def stop(self):
        self._running = False
        if self._proc:
            try:
                self.send({"type": "abort"})
            except Exception:
                pass
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
            self._proc = None

    @property
    def is_running(self) -> bool:
        return self._running and (self._proc is not None and self._proc.poll() is None)


# ================================================================
# Audio Capture & VAD & STT
# ================================================================

class AudioCapture:
    """Cattura audio dal microfono con VAD e trascrizione whisper."""

    def __init__(self, config: Config):
        self.config = config
        self._stream: Optional[sd.RawInputStream] = None
        self._running = False
        self._vad = None
        if config.vad_enabled:
            import webrtcvad  # type: ignore
            self._vad = webrtcvad.Vad(config.vad_aggressiveness)
        self._oww = None
        if config.mode == "wakeword":
            try:
                from openwakeword import Model as OWWModel  # type: ignore
                self._oww = OWWModel(
                    wakeword_models=["hey_jarvis"],
                    inference_framework="onnx",
                )
                log.info("Wake word model 'hey jarvis' caricato")
            except Exception as e:
                log.warning(f"openwakeword non disponibile: {e}")
                log.info("Wake word via trascrizione VAD (prefisso 'jarvis' nel testo)")
        self._whisper = None
        self._whisper_lock = threading.Lock()

    def _lazy_whisper(self):
        if self._whisper is None:
            from faster_whisper import WhisperModel  # type: ignore
            log.info(
                f"Caricamento whisper model='{self.config.whisper_model}' "
                f"device={self.config.whisper_device} "
                f"compute={self.config.whisper_compute}"
            )
            self._whisper = WhisperModel(
                self.config.whisper_model,
                device=self.config.whisper_device,
                compute_type=self.config.whisper_compute,
            )
            log.info("Whisper pronto")
        return self._whisper

    def transcribe(self, audio_bytes: bytes) -> str:
        with self._whisper_lock:
            model = self._lazy_whisper()
            audio_np = (
                np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )
            segments, info = model.transcribe(
                audio_np,
                language=self.config.whisper_lang,
                beam_size=5,
                vad_filter=False,
                no_speech_threshold=0.6,
            )
            text = " ".join(seg.text for seg in segments).strip()
            return text

    def start_stream(self, callback: callable):
        self._running = True
        device = self.config.audio_device
        if device is not None:
            sd.default.device = device
        self._stream = sd.RawInputStream(
            samplerate=self.config.audio_sr,
            blocksize=self.config.audio_blocksize,
            channels=self.config.audio_channels,
            dtype="int16",
            callback=lambda indata, frames, time_info, status: (
                callback(bytes(indata)) if self._running else None
            ),
        )
        self._stream.start()

    def stop_stream(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def is_speech(self, chunk: bytes) -> bool:
        """VAD: True se il chunk contiene voce. 30ms = 960 bytes a 16kHz."""
        if self._vad is None:
            return True
        if len(chunk) < 960:
            return False
        return self._vad.is_speech(chunk[:960], self.config.audio_sr)


# ================================================================
# TTS Engine
# ================================================================

class TTSManager:
    """Sintesi vocale: edge-tts (online) con riproduzione pygame."""

    def __init__(self, config: Config):
        self.config = config
        self._engine = config.tts_engine

    def speak(self, text: str):
        if not text.strip():
            return
        log.info(f"Jarvis: {text[:120]}...")
        if self._engine == "piper":
            self._speak_piper(text)
        else:
            self._speak_edge(text)

    def _speak_edge(self, text: str):
        try:
            import edge_tts  # type: ignore
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()
            async def _do():
                comm = edge_tts.Communicate(
                    text, self.config.tts_voice,
                    rate=self.config.tts_rate, volume=self.config.tts_volume,
                )
                await comm.save(tmp_path)
            asyncio.run(_do())
            self._play_audio(tmp_path)
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        except Exception as e:
            log.error(f"edge-tts fallito: {e}")
            # fallback silenzioso
            print(f"\n--- Jarvis (fallback) ---\n{text}\n---")

    def _play_audio(self, path: str):
        """Riproduce file audio: pygame MP3, fallback winsound WAV."""
        try:
            import pygame  # type: ignore
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
        except Exception:
            try:
                if sys.platform == "win32" and path.endswith(".wav"):
                    import winsound  # type: ignore
                    winsound.PlaySound(path, winsound.SND_FILENAME)
            except Exception:
                pass


# ================================================================
# Wake Word via Trascrizione
# ================================================================

def ascolta_e_comandi(audio: AudioCapture, pi: PiRPCClient, tts: TTSManager):
    """
    Loop principale semplificato:
    - Buffer circolare di N secondi
    - Quando si preme INVIO: trascrive il buffer e invia a pi
    - Oppure: VAD semplice (energia) + timeout silenzio
    """
    wake_word = RAW_CFG.get("wake_word", "jarvis").lower()
    sr = CFG.audio_sr
    block_ms = int(CFG.audio_blocksize / sr * 1000)  # ms per chunk

    buffer = bytearray()
    speech_frames = 0
    silence_frames = 0
    is_recording = False
    max_silence_frames = int(CFG.ptt_silence_timeout * 1000 / block_ms)
    min_phrase_frames = int(CFG.ptt_min_phrase * 1000 / block_ms)

    def rms(chunk: bytes) -> float:
        """Energia RMS del chunk audio."""
        arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float64)
        if len(arr) == 0:
            return 0.0
        return np.sqrt(np.mean(arr ** 2))

    def on_chunk(chunk: bytes):
        nonlocal buffer, speech_frames, silence_frames, is_recording

        energy = rms(chunk)
        threshold = 800.0  # soglia energia voce (evita rumori ambientali)

        if energy > threshold:
            silence_frames = 0
            speech_frames += 1
            if not is_recording and speech_frames > 2:
                is_recording = True
                log.info(f"[VAD] INIZIO (energia={energy:.0f})")
            if is_recording:
                buffer.extend(chunk)
        else:
            if is_recording:
                silence_frames += 1
                buffer.extend(chunk)
                if silence_frames > max_silence_frames:
                    log.info(f"[VAD] FINE (silenzio={silence_frames} frames, buffer={len(buffer)} bytes)")
                    process_phrase()
            else:
                speech_frames = 0

    def process_phrase():
        nonlocal buffer, is_recording, speech_frames, silence_frames
        is_recording = False
        speech_frames = 0
        silence_frames = 0

        audio_len_s = len(buffer) / (sr * 2)
        if audio_len_s < CFG.ptt_min_phrase:
            log.debug(f"Frase troppo corta ({audio_len_s:.1f}s)")
            buffer.clear()
            return

        log.info(f"Trascrizione ({audio_len_s:.1f}s)...")
        testo = audio.transcribe(bytes(buffer))
        buffer.clear()

        if not testo:
            log.debug("Trascrizione vuota")
            return

        log.info(f"Utente: {testo}")

        # Gestione wake word
        if CFG.mode == "wakeword":
            testo_lower = testo.lower().strip()
            if not testo_lower.startswith(wake_word):
                return
            testo = testo[len(wake_word):].strip().lstrip(",. !?")
            if not testo:
                tts.speak("Dimmi pure")
                return

        # Comando vocale di uscita
        if "esci" in testo.lower() or "chiudi" in testo.lower():
            tts.speak("Arrivederci")
            pi.stop()
            audio.stop_stream()
            sys.exit(0)

        # Invia a pi
        log.info("Invio a pi...")
        ok = pi.prompt(testo)
        if not ok:
            tts.speak("Non ho potuto contattare pi")
            return

    def on_pi_event(ev_type: str, data):
        if ev_type == "agent_settled" and data:
            tts.speak(data)

    pi.add_event_callback(on_pi_event)

    log.info(f"In ascolto (mode={CFG.mode})...")
    log.info(f"  Wake word: '{wake_word}'" if CFG.mode == "wakeword" else "  PTT: parlare liberamente")
    log.info("  Dì 'esci' o 'chiudi' per uscire")

    try:
        audio.start_stream(on_chunk)
        while pi.is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        log.info("Interruzione...")
    finally:
        audio.stop_stream()
        pi.stop()


# ================================================================
# Main
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Jarvis — Assistente vocale per pi agent")
    parser.add_argument("--mode", choices=["wakeword", "ptt"],
                        default=CFG.mode,
                        help="Modalita: wakeword (default) o ptt (sempre in ascolto)")
    parser.add_argument("--model", help="Modello pi (es. openrouter/z-ai/glm-5.2)")
    parser.add_argument("--whisper", help="Modello whisper (tiny, base, small, medium)")
    parser.add_argument("--tts", choices=["edge", "piper"],
                        help="Motore TTS")
    args = parser.parse_args()

    if args.mode:
        CFG.mode = args.mode
    if args.whisper:
        CFG.whisper_model = args.whisper
    if args.tts:
        CFG.tts_engine = args.tts
    if args.model:
        CFG.pi_model = args.model

    log.info(f"Jarvis — Assistente vocale per pi agent")
    log.info(f"  Mode: {CFG.mode}")
    log.info(f"  Whisper: {CFG.whisper_model}")
    log.info(f"  TTS: {CFG.tts_engine} ({CFG.tts_voice})")
    log.info(f"  Pi model: {CFG.pi_model or 'default'}")
    log.info(f"  Pi cwd: {CFG.pi_cwd}")

    audio = AudioCapture(CFG)
    pi = PiRPCClient(CFG)
    tts = TTSManager(CFG)

    try:
        pi.start()
        tts.speak("Jarvis avviato. Pronto ad aiutarti.")
        ascolta_e_comandi(audio, pi, tts)
    except Exception as e:
        log.error(f"Errore: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pi.stop()
        audio.stop_stream()


if __name__ == "__main__":
    main()
