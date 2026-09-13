# Browser Review

Before opening the browser, tell the user which plan file to review and what to
check. Use a dedicated plan artifact, not an unrelated or newest file, and keep
the viewer open until the user says review is finished.

`mdv` walks upward from a requested port when needed. Never search for a free
port first. Parse the real URL printed on startup instead of assuming the port:

```bash
mdv -d -n -q <path> 2>&1 | grep -o 'http://127\.0\.0\.1:[0-9]*'
```

For a small self-contained directory, run `mdv -d -n -q <directory>`, parse the
printed port, and stop that instance with `mdv stop --port <parsed-port>` after
the user finishes. Never close it on a timer.
