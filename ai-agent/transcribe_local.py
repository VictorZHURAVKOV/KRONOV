"""Локальная транскрибация всех .aac через faster-whisper large-v3.

Первый запуск скачает модель ~1.5 GB из HuggingFace. Дальше — из кеша.
Результаты пишет в data/transcripts/<stem>.txt.
Для Apple Silicon автоматически использует оптимизированный CTranslate2.
"""
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel

SRC = Path("/Users/viktor/Downloads/записи")
DST = Path(__file__).parent / "data" / "transcripts"
DST.mkdir(parents=True, exist_ok=True)

# Модель. large-v3 — топовая для русского. int8 — быстро на CPU (M4).
MODEL = "large-v3"
COMPUTE = "int8"

print(f"Загружаю модель {MODEL} (compute={COMPUTE})...", flush=True)
t0 = time.time()
model = WhisperModel(MODEL, device="cpu", compute_type=COMPUTE)
print(f"  Загружено за {time.time() - t0:.1f}s", flush=True)

files = sorted(SRC.glob("*.aac"))
print(f"Файлов для транскрибации: {len(files)}", flush=True)
print("=" * 60, flush=True)

total_start = time.time()
for i, f in enumerate(files, 1):
    out = DST / (f.stem + ".txt")
    if out.exists() and out.stat().st_size > 100:
        print(f"[{i:>2}/{len(files)}] SKIP {f.name}", flush=True)
        continue

    t = time.time()
    try:
        segments, info = model.transcribe(
            str(f),
            language="ru",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        # Stream segments в файл
        lines = []
        for seg in segments:
            # Формат: [mm:ss — mm:ss] текст
            mm_s = int(seg.start // 60); ss_s = int(seg.start % 60)
            mm_e = int(seg.end // 60); ss_e = int(seg.end % 60)
            lines.append(f"[{mm_s:02d}:{ss_s:02d}-{mm_e:02d}:{ss_e:02d}] {seg.text.strip()}")
        text = "\n".join(lines)
        out.write_text(text, encoding="utf-8")
        elapsed = time.time() - t
        print(f"[{i:>2}/{len(files)}] OK  {f.name} — {info.duration:.1f}s аудио → {len(text)} симв за {elapsed:.1f}s", flush=True)
    except Exception as e:
        print(f"[{i:>2}/{len(files)}] FAIL {f.name}: {e}", flush=True)

print("=" * 60, flush=True)
print(f"Всего времени: {time.time() - total_start:.1f}s", flush=True)
print(f"Результаты: {DST}", flush=True)
