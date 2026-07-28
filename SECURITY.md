# Security

## Supported version

Security fixes are applied to the latest commit on the default branch.

## Reporting

Use GitHub private vulnerability reporting when it is available for this
repository. Do not place exploit details, credentials, private video links,
signed URLs, cookies, transcripts, or downloaded frames in a public issue.

For non-sensitive bugs, open a regular issue with a minimal reproduction that
uses public or synthetic media.

## Security model

The skill treats video audio, subtitles, metadata, and on-screen text as
untrusted data. It must not follow instructions embedded in media. The bundled
scripts perform local processing and do not upload artifacts.

The project does not support bypassing authentication, DRM, paywalls, or access
controls.
