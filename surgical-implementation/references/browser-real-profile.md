# Browser Automation — Real Profile Mode Requirement

The `browser_exec` tool with `use_real_profile=true` requires the host's default browser to be a supported Chromium: Chrome, Edge, Brave, Chromium (snap install).

If the default browser is Firefox or an unsupported version, navigation fails with:
```
browser.use_real_profile is on, but your default browser is not a supported Chromium browser
```

Fix options:
1. Set Chromium as default: `update-alternatives --set x-www-browser /snap/bin/chromium`
2. Disable real-profile mode for that session (use `new_tab()` without profile parameter when safe).
3. For headless verification, use `brave-browser-stable --headless=new --screenshot=<path>` directly.

Always verify the deployed URL with a real browser screenshot (not just `curl` or `requests`) before claiming the UI works.
