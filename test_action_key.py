"""Wait five seconds, press F6 once, then exit."""

import time

import keyboard


ACTION_KEY = "f6"
HOLD_SECONDS = 0.12


print("F6 input test")
print("Switch to Delta Force now. F6 will be pressed once after five seconds.")
for remaining in range(5, 0, -1):
    print(f"{remaining}...")
    time.sleep(1)

keyboard.press(ACTION_KEY)
try:
    time.sleep(HOLD_SECONDS)
finally:
    keyboard.release(ACTION_KEY)

print("F6 was sent. The test is finished.")
