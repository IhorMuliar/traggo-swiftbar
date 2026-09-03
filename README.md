# traggo-swiftbar

Start and stop [Traggo](https://traggo.net) time tracking per project from the macOS menu bar.
A single-file [SwiftBar](https://swiftbar.app) plugin, plain Python, no dependencies beyond the
system interpreter.

```
⏱            idle
▶ doges 1:23 tracking "project:doges" for 1h23m (refreshes every 30s)
⏱ ✕          server unreachable
```

Menu items: **Stop**, **Start `<project>`** / **Switch to `<project>`** (stops the running
timer first), **Today** totals split by project, **Open Traggo**.

Traggo is tag-based. This plugin assumes one tag key (default `project`) whose value is the
project name. Values you list in the config are always offered; values already used on the
server are merged in automatically.

## Install

1. `brew install --cask swiftbar` and pick a plugin folder on first launch (or
   `defaults write com.ameba.SwiftBar PluginDirectory ~/.swiftbar/plugins`).
2. Put `traggo.30s.py` in that folder, or symlink it from a clone of this repo. Make it executable.
3. Create a config file at `~/.config/traggo-swiftbar/config.json`:

   ```json
   {
     "url": "https://traggo.example.com",
     "tag_key": "project",
     "projects": ["alpha", "beta"],
     "keychain_service": "traggo-swiftbar",
     "keychain_account": "yourname"
   }
   ```

4. Create a device token in Traggo and store it in the macOS Keychain. In the Traggo web UI go
   to **User → Devices**, add a device of type *NoExpiry*, copy the token, then:

   ```
   security add-generic-password -s traggo-swiftbar -a yourname -w '<token>' -T /usr/bin/security
   ```

   Or do it in one go through the API:

   ```
   curl -s https://traggo.example.com/graphql -H 'content-type: application/json' \
     -d '{"query":"mutation { login(username:\"yourname\", pass:\"...\", deviceName:\"swiftbar\", type: NoExpiry, cookie:false) { token } }"}'
   ```

5. Refresh SwiftBar. The token never touches the plugin file or the config.

## Notes

- Refresh interval is encoded in the filename (`30s`). Rename to change it.
- Actions call the same script: `traggo.30s.py start <project>` and `traggo.30s.py stop`.
  Handy for Raycast, Shortcuts or a hotkey.
- Traggo's `Time` scalar is strict RFC 3339 with a colon in the offset; the plugin uses
  `isoformat()` for that reason.
- Requires macOS with SwiftBar and `/usr/bin/python3` (Xcode Command Line Tools).

## License

MIT
