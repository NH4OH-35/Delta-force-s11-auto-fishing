"""Record Windows speaker output through WASAPI loopback.

Run:
    py record_bite.py

Press Ctrl+C to stop. The recording is saved as bite.wav.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import soundcard as sc
from scipy.io import wavfile


SAMPLE_RATE = 48_000
BLOCK_SIZE = 1_024
OUTPUT_FILE = Path(__file__).with_name("bite.wav")


def get_loopback_devices():
    devices = sc.all_microphones(include_loopback=True)
    return [device for device in devices if getattr(device, "isloopback", False)]


def choose_device():
    default_speaker = sc.default_speaker()
    loopbacks = get_loopback_devices()

    print(f"当前默认播放设备: {default_speaker.name}")

    if loopbacks:
        print("\n可用的系统输出/Loopback 设备:")
        for index, device in enumerate(loopbacks, start=1):
            print(f"  {index}. {device.name}")

        matching = [
            device
            for device in loopbacks
            if device.name == default_speaker.name
            or default_speaker.name in device.name
            or device.name in default_speaker.name
        ]
        recommended = loopbacks.index(matching[0]) + 1 if matching else 1
        answer = input(f"\n输入设备编号，直接回车使用推荐设备 [{recommended}]: ").strip()

        if not answer:
            return loopbacks[recommended - 1]

        try:
            selected = loopbacks[int(answer) - 1]
        except (ValueError, IndexError):
            print("设备编号无效。")
            sys.exit(1)
        return selected

    # Fallback for versions/drivers that do not expose loopbacks in the list.
    print("没有列出 Loopback 设备，尝试绑定默认播放设备。")
    return sc.get_microphone(id=str(default_speaker.name), include_loopback=True)


def save_wav(chunks):
    audio = np.concatenate(chunks, axis=0)

    # Convert stereo/multichannel to mono. This is convenient for later matching
    # and still contains the complete game sound mix.
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    audio = np.asarray(audio, dtype=np.float32)
    audio = np.nan_to_num(audio)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        audio /= peak

    pcm16 = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm16 * 32767).astype(np.int16)
    wavfile.write(OUTPUT_FILE, SAMPLE_RATE, pcm16)

    duration = len(pcm16) / SAMPLE_RATE
    print(f"\n已保存: {OUTPUT_FILE}")
    print(f"时长: {duration:.1f} 秒，采样率: {SAMPLE_RATE} Hz，单声道")


def main():
    print("Delta Force 鱼咬钩声音录制器")
    print("请先让游戏运行，并把音量调到平时钓鱼时的音量。")

    try:
        device = choose_device()
        print(f"\n将录制设备: {device.name}")
        print("现在回到游戏，开始钓鱼。听到鱼咬钩后继续录几秒，然后回到这里按 Ctrl+C。")
        input("准备好后按 Enter 开始录制...")
    except KeyboardInterrupt:
        print("\n已取消。")
        return
    except Exception as exc:
        print(f"无法打开音频设备: {exc}")
        print("请检查 Windows 的默认输出设备，或重新运行后选择正确的 Loopback 设备。")
        sys.exit(1)

    chunks = []
    started = time.monotonic()
    try:
        with device.recorder(
            samplerate=SAMPLE_RATE,
            channels=None,
            blocksize=BLOCK_SIZE,
        ) as recorder:
            while True:
                chunks.append(recorder.record(numframes=BLOCK_SIZE))
                elapsed = time.monotonic() - started
                print(f"\r录制中 {elapsed:6.1f} 秒 | Ctrl+C 停止", end="", flush=True)
    except KeyboardInterrupt:
        pass

    if not chunks:
        print("\n没有录到音频。")
        return
    save_wav(chunks)


if __name__ == "__main__":
    main()
