"""Delta Force fishing helper driven by a bite-sound template.

Cycle:
    press the configured action key to cast
    wait 1.5 seconds and press the action key again
    ignore audio for 5 seconds
    listen for bite sound until 20 seconds after casting
    wait a random 0.214-0.578 seconds after a bite, then press the action key
    press the action key at the 20-second timeout if there is no bite
    wait a random 7-9 seconds for the animation
    repeat

Press F8 at any time to stop.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import keyboard
import numpy as np
import soundcard as sc
from scipy.io import wavfile
from scipy.signal import correlate, resample_poly


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = BASE_DIR / "bite_clean_10.5_to_12.wav"

SAMPLE_RATE = 48_000
BLOCK_SIZE = 1_024
IGNORE_AFTER_CAST_SECONDS = 5.0
MAX_CAST_SECONDS = 20.0
ANIMATION_WAIT_MIN_SECONDS = 7.0
ANIMATION_WAIT_MAX_SECONDS = 9.0
MATCH_THRESHOLD = 0.58
START_COUNTDOWN_SECONDS = 5
STOP_KEY = "f8"
ACTION_KEY = "f6"
ACTION_KEY_HOLD_SECONDS = 0.12
BITE_REACTION_DELAY_MIN_SECONDS = 0.214
BITE_REACTION_DELAY_MAX_SECONDS = 0.578
SECOND_CAST_PRESS_DELAY_SECONDS = 1.5


def stop_requested() -> bool:
    return keyboard.is_pressed(STOP_KEY)


def wait_interruptibly(seconds: float) -> bool:
    """Wait for up to seconds. Return False when F8 was pressed."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if stop_requested():
            return False
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    return True


def press_fishing_action():
    """Press and release the in-game key bound to cast/reel."""
    keyboard.press(ACTION_KEY)
    try:
        time.sleep(ACTION_KEY_HOLD_SECONDS)
    finally:
        keyboard.release(ACTION_KEY)


def choose_loopback_device():
    default_speaker = sc.default_speaker()
    speakers = sc.all_speakers()
    print(f"Windows 当前默认播放设备：{default_speaker.name}")
    print("可用的 Windows 播放设备：")
    for index, speaker in enumerate(speakers, start=1):
        default_mark = " [默认]" if speaker.id == default_speaker.id else ""
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
        f"输入游戏使用的设备 A 编号，直接按 Enter 使用 [{recommended}]："
    ).strip()

    try:
        selected_index = recommended if not answer else int(answer)
        selected_speaker = speakers[selected_index - 1]
    except (ValueError, IndexError):
        raise RuntimeError("设备编号无效。")

    try:
        loopback = sc.get_microphone(
            id=selected_speaker.id,
            include_loopback=True,
        )
    except Exception as exc:
        raise RuntimeError(
            f"无法打开设备 A 的 loopback：{selected_speaker.name}"
        ) from exc

    print(f"已严格监听设备 A：{selected_speaker.name}")
    print(f"设备 A 端点 ID：{selected_speaker.id}")
    return loopback


def load_template(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"找不到咬钩声音模板：{path}")

    rate, audio = wavfile.read(path)
    audio = np.asarray(audio)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    if np.issubdtype(audio.dtype, np.integer):
        max_value = max(abs(np.iinfo(audio.dtype).min), np.iinfo(audio.dtype).max)
        audio = audio.astype(np.float32) / max_value
    else:
        audio = audio.astype(np.float32)

    if rate != SAMPLE_RATE:
        divisor = np.gcd(rate, SAMPLE_RATE)
        audio = resample_poly(audio, SAMPLE_RATE // divisor, rate // divisor)

    audio -= np.mean(audio)
    norm = float(np.linalg.norm(audio))
    if norm < 1e-8:
        raise RuntimeError("咬钩声音模板是静音，无法使用。")

    return audio, norm


def to_mono_float(audio):
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return np.nan_to_num(audio)


def match_score(audio, template, template_norm) -> float:
    """Return the highest normalized waveform similarity in the audio window."""
    audio = np.asarray(audio, dtype=np.float64)
    template = np.asarray(template, dtype=np.float64)
    width = len(template)
    if len(audio) < width:
        return 0.0

    correlation = correlate(audio, template, mode="valid", method="fft")

    cumulative = np.concatenate(([0.0], np.cumsum(audio)))
    cumulative_sq = np.concatenate(([0.0], np.cumsum(audio * audio)))
    window_sum = cumulative[width:] - cumulative[:-width]
    window_sq_sum = cumulative_sq[width:] - cumulative_sq[:-width]
    window_energy = window_sq_sum - (window_sum * window_sum / width)
    denominator = np.sqrt(np.maximum(window_energy, 1e-12)) * template_norm

    scores = correlation / denominator
    return float(np.clip(np.max(scores), -1.0, 1.0))


def listen_for_bite(device, seconds, template, template_norm):
    chunks = []
    max_samples = len(template) + SAMPLE_RATE
    highest_score = 0.0
    deadline = time.monotonic() + seconds
    blocks_since_check = 0

    with device.recorder(
        samplerate=SAMPLE_RATE,
        channels=None,
        blocksize=BLOCK_SIZE,
    ) as recorder:
        while time.monotonic() < deadline:
            if stop_requested():
                return "stopped", highest_score

            chunks.append(to_mono_float(recorder.record(numframes=BLOCK_SIZE)))
            blocks_since_check += 1

            total_samples = sum(len(chunk) for chunk in chunks)
            while len(chunks) > 1 and total_samples - len(chunks[0]) >= max_samples:
                total_samples -= len(chunks[0])
                chunks.pop(0)

            if blocks_since_check < 6:
                continue
            blocks_since_check = 0

            window = np.concatenate(chunks)
            score = match_score(window, template, template_norm)
            highest_score = max(highest_score, score)
            remaining = max(0.0, deadline - time.monotonic())
            print(
                f"\r监听咬钩声 | 相似度 {score:.2f} | 剩余 {remaining:4.1f} 秒",
                end="",
                flush=True,
            )

            if score >= MATCH_THRESHOLD:
                print(f"\n检测到咬钩声音，相似度 {score:.2f}。")
                return "bite", highest_score

    print(f"\n20 秒内没有检测到咬钩；最高相似度 {highest_score:.2f}。")
    return "timeout", highest_score


def run_bot():
    template, template_norm = load_template(TEMPLATE_FILE)
    device = choose_loopback_device()

    print(f"\n使用声音模板：{TEMPLATE_FILE.name}")
    print(f"监听设备：{device.name}")
    print(f"请先在游戏设置中把抛竿/收竿绑定到 {ACTION_KEY.upper()}。")
    print("运行后请保持游戏在最前面。按 F8 可随时停止。")
    input("准备好后按 Enter，然后立刻切回游戏：")

    for remaining in range(START_COUNTDOWN_SECONDS, 0, -1):
        if stop_requested():
            print("已停止。")
            return
        print(f"{remaining} 秒后开始……")
        time.sleep(1)

    cycle = 0
    while not stop_requested():
        cycle += 1
        print(f"\n第 {cycle} 轮：按 {ACTION_KEY.upper()} 抛竿。")
        press_fishing_action()

        print(f"等待 {SECOND_CAST_PRESS_DELAY_SECONDS:.1f} 秒后再次按 {ACTION_KEY.upper()}。")
        if not wait_interruptibly(SECOND_CAST_PRESS_DELAY_SECONDS):
            break
        press_fishing_action()
        cast_time = time.monotonic()

        print("前 5 秒不监听。")
        if not wait_interruptibly(IGNORE_AFTER_CAST_SECONDS):
            break

        listen_seconds = max(0.0, MAX_CAST_SECONDS - (time.monotonic() - cast_time))
        result, _ = listen_for_bite(
            device,
            listen_seconds,
            template,
            template_norm,
        )
        if result == "stopped":
            break

        if result == "bite":
            reaction_delay = random.uniform(
                BITE_REACTION_DELAY_MIN_SECONDS,
                BITE_REACTION_DELAY_MAX_SECONDS,
            )
            print(f"检测到咬钩，随机等待 {reaction_delay:.3f} 秒后收竿。")
            if not wait_interruptibly(reaction_delay):
                break

        print(f"按 {ACTION_KEY.upper()} 收竿。")
        press_fishing_action()

        animation_wait = random.uniform(
            ANIMATION_WAIT_MIN_SECONDS,
            ANIMATION_WAIT_MAX_SECONDS,
        )
        print(f"等待收竿动画 {animation_wait:.1f} 秒。")
        if not wait_interruptibly(animation_wait):
            break

    print("\n机器人已停止，不会再点击鼠标。")


def main():
    print("Delta Force 自动钓鱼声音检测器")
    print("提示：请只在游戏规则允许自动化的情况下使用。\n")
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n已停止。")
    except Exception as exc:
        print(f"\n运行失败：{exc}")
        print("窗口会保留，方便查看错误。")
        sys.exit(1)


if __name__ == "__main__":
    main()
