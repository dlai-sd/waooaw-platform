# WC-085 Browser Evidence

Scope: local production Next.js build with synthetic BP fixture; code freeze `14a28c18aa8774d8b2f956c475e2e60a245f4ddd`.
Not a live Demo or Founder visual acceptance record.

Command, inside `mcr.microsoft.com/playwright:v1.62.1-noble` with the web source and dependency volume:

```sh
./node_modules/.bin/playwright test wc085-auth.spec.ts wc083-auth-dialog.spec.ts --workers=2 --reporter=line
```

Result: 30 passed, zero failed, five configured projects. The server command performs a production build.

| Project | Default Viewport | Explicit Case Overrides | Result |
|---|---|---|---|
| chromium-expanded | 1440x900 | WC-085 cases set 1366x768; RTL axe case sets 360x800 | 6/6 PASS locally |
| firefox-expanded | 1440x900 | Same overrides | 6/6 PASS locally |
| webkit-expanded | 1440x900 | Same overrides | 6/6 PASS locally |
| chromium-compact-360 | 360x800, Pixel 7 emulation | WC-085 cases deliberately set 1366x768; not a mobile result for those cases | 6/6 PASS locally |
| chromium-intermediate | 768x1024 | WC-085 cases set 1366x768; RTL axe case sets 360x800 | 6/6 PASS locally |

Assertions cover initial login/register no-scroll geometry at 1366x768, stable width/height across
login-to-register, Escape directly to `/professionals` with restored focus, home Close, backdrop,
standalone auth routes, fixture provider states, Urdu RTL dark 360px no horizontal overflow,
reduced-motion and no serious/critical axe violations in the auth dialog.

Desktop login and registration full-page PNG captures were inspected: dialog text and choices fit,
Close remains visible, and the preserved public page remains behind the modal. Captures reside in
`web/test-results/wc085-auth-*/`; their filenames describe actual 1366px viewport, not project defaults.
They are reproducible supporting artifacts, not baseline visual diffs or Founder acceptance.

Missing: full 125%/200% zoom, font delay, server streaming loading/error interaction, all provider states,
every public/portal route, exact deployed revision, and substantive Founder visual acceptance.
SP-01/02/07/08/18 remain PARTIAL; SP-09 and SP-22 are BLOCKED.