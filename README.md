
# Codex Usage Lock Screen Widget

A compact Scriptable Lock Screen widget that shows the percentage **remaining** in your Codex usage windows:

<img width="236" height="190" alt="IMG_3227" src="https://github.com/user-attachments/assets/f761d9da-db1e-4baa-9252-af29d60c9d53" />

```text
>> CODEX
05H 100%
07D 063% 20.07
```

The Mac refreshes the data every 15 minutes while awake. Scriptable syncs it to the iPhone through iCloud Drive.

## Requirements

- macOS and iPhone signed into the same iCloud account
- [Scriptable](https://scriptable.app/) installed on the iPhone with iCloud enabled
- ChatGPT or Codex desktop app installed in `/Applications` and signed in
- Python 3 on the Mac

This project uses the Codex executable bundled with the ChatGPT or Codex desktop app. It does **not** install or require a separate Codex CLI, and it does not copy or expose authentication tokens.

## Install

1. Open Scriptable once on the iPhone and enable iCloud for Scriptable.
2. Open the ChatGPT or Codex desktop app on the Mac and sign in.
3. Clone this repository and run:

   ```bash
   chmod +x install.sh
   ./install.sh
   ```

4. If macOS asks, allow Terminal or Codex to access iCloud Drive and install the user LaunchAgent.
5. On the iPhone, open Scriptable and run **Codex Usage** once.
6. Long-press the Lock Screen, choose **Customize**, tap the widget area, add **Scriptable**, choose the rectangular widget, and select **Codex Usage**.

## What gets installed

| Item | Location |
| --- | --- |
| Widget script | `~/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents/Codex Usage.js` |
| Mac updater | `~/.local/share/codex-usage-widget/codex_usage_to_icloud.py` |
| Usage data | Scriptable's iCloud folder as `codex-limits.json` |
| LaunchAgent | `~/Library/LaunchAgents/com.openai.codex-usage-widget.plist` |
| Logs | `/tmp/codex-usage-widget.log` and `/tmp/codex-usage-widget.err` |

The LaunchAgent uses `StartInterval = 900`, so it runs every 15 minutes while the Mac is awake. iOS controls the exact Lock Screen widget refresh time.

## Verify

Run the updater manually:

```bash
~/.local/share/codex-usage-widget/codex_usage_to_icloud.py
```

Check the generated data and service:

```bash
ls -l "$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents/codex-limits.json"
launchctl print "gui/$(id -u)/com.openai.codex-usage-widget"
tail -n 20 /tmp/codex-usage-widget.log
tail -n 20 /tmp/codex-usage-widget.err
```

## Display behavior

- Percentages are percentage remaining, not percentage used.
- `05H` shows its local reset time only when Codex supplies one.
- `07D` shows its local reset date as `DD.MM`.
- Missing reset information is omitted.

## Uninstall

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.openai.codex-usage-widget.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.openai.codex-usage-widget.plist"
rm -rf "$HOME/.local/share/codex-usage-widget"
rm -f "$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents/Codex Usage.js"
```

The uninstall commands intentionally leave `codex-limits.json` in place. Remove it separately if desired.
