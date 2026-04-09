# Session ID Defaults

Status: Implemented
Date: 2026-04-09

## Conclusion

When a session id is not explicitly provided, Sparrow Agent now creates a random one instead of reusing a fixed default.

## Decisions

- CLI no longer defaults to `default`
- Web no longer uses the hard-coded `web-demo`
- generated ids stay filename-safe and readable

## Shape

- CLI resolves a missing `--session-id` to a generated id with a `cli-` prefix
- Web creates a generated id with a `web-` prefix and keeps it in `sessionStorage`

This keeps adapters thin and avoids changing the existing runtime or server API shape.
