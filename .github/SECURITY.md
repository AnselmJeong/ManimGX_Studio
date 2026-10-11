# Security policy

## Reporting a vulnerability

Please don't report a vulnerability in a public issue. Report it privately, through
[GitHub's private vulnerability reporting](https://github.com/academa-labs/manimgx/security/advisories/new)
or by email to [security@academa.ai](mailto:security@academa.ai).

Tell us what you found, how to reproduce it (a scene or an input file helps most), and the
ManimGX version. We acknowledge every report within 7 days, and keep you updated while we work
on a fix. When it is fixed, we publish a
[security advisory](https://github.com/academa-labs/manimgx/security/advisories), with a CVE
where one applies, and credit you unless you'd rather not be named.

## Supported versions

Fixes go into the latest release.

## Scope

A scene is a Python program, and rendering it runs its code with your permissions. Rendering
an untrusted scene is running untrusted code: that is how ManimGX works, not a vulnerability.

In scope is anything that lets input meant as data run code, read or write files, or corrupt
memory: an SVG, an image or a font, or the text and math ManimGX typesets.
