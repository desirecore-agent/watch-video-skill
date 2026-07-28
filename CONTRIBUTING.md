# Contributing

Contributions that improve portability, timestamp accuracy, scene selection, or
runtime compatibility are welcome.

## Before opening a change

1. Keep the skill runtime-neutral and free of user-specific paths or rules.
2. Do not add private media, downloaded frames, transcripts, cookies, or tokens.
3. Keep `skills/watch/SKILL.md` concise and use imperative instructions.
4. Preserve Bash 3.2 compatibility for shell scripts.
5. Run:

   ```bash
   python3 scripts/validate_public.py
   ```

6. Test installer changes with a temporary home directory.

Use synthetic or freely redistributable media fixtures in tests. Describe the
platform, runtime, command, expected behavior, and actual behavior in bug
reports without including sensitive content.
