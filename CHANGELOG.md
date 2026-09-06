# Version 2

## Changes

- Returned to the stable `F6`-based workflow.
- Presses `F6` once, waits 1.5 seconds, and presses `F6` again to handle the bait prompt that can appear every five casts.
- Starts bite-sound monitoring 5 seconds after the second `F6` press.
- Reels in after a random 0.214–0.578-second reaction delay when a bite is detected.
- Reels in automatically when the 20-second timeout is reached.
- Waits a random 7–9 seconds after reeling in before beginning the next cycle.
- Binds audio capture to the selected Windows playback endpoint by its unique device ID.

## Required setup

- Run `start_fishing_bot.bat` as administrator.
- Keep left mouse as the primary fishing/shooting control and add `F6` as the secondary control.
- Select the exact Windows output device used by Delta Force when the program starts.
- Press `F8` to stop the program.
