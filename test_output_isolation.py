"""Record one selected Windows output endpoint for an isolation check."""

from pathlib import Path

import numpy as np
import soundcard as sc
from scipy.io import wavfile


SAMPLE_RATE = 48_000
DURATION_SECONDS = 8
OUTPUT_FILE = Path(__file__).with_name("output_isolation_test.wav")


def main():
    default_speaker = sc.default_speaker()
    speakers = sc.all_speakers()

    print(f"Windows current default output: {default_speaker.name}")
    print("Available output endpoints:")
    for index, speaker in enumerate(speakers, start=1):
        default_mark = " [default]" if speaker.id == default_speaker.id else ""
        print(f"  {index}. {speaker.name}{default_mark}")

    recommended = next(
        (
            index
            for index, speaker in enumerate(speakers, start=1)
            if speaker.id == default_speaker.id
        ),
        1,
    )
    answer = input(
        f"Select device A by number, or press Enter for [{recommended}]: "
    ).strip()
    selected_index = recommended if not answer else int(answer)
    selected_speaker = speakers[selected_index - 1]
    loopback = sc.get_microphone(
        id=selected_speaker.id,
        include_loopback=True,
    )

    print(f"Selected: {selected_speaker.name}")
    print(f"Endpoint ID: {selected_speaker.id}")
    input(
        "Play only the Bilibili video routed to device B, then press Enter "
        "to record device A for 8 seconds..."
    )

    with loopback.recorder(samplerate=SAMPLE_RATE, channels=None) as recorder:
        audio = recorder.record(numframes=SAMPLE_RATE * DURATION_SECONDS)

    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    audio = np.nan_to_num(audio)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(audio * audio))) if audio.size else 0.0
    pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(OUTPUT_FILE, SAMPLE_RATE, pcm16)

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Peak level: {peak:.6f}")
    print(f"RMS level:  {rms:.6f}")
    print("Listen to the WAV file and check whether it contains Bilibili audio.")


if __name__ == "__main__":
    main()
