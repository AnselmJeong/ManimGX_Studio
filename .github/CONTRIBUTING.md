# Contributing to ManimGX

Thank you for helping. ManimGX is developed and maintained by [Academa](https://academa.ai):
its maintainers review every change, and decide what is merged and where the project goes.

This page is how to take part. How ManimGX works, and how to set it up, change it and test it,
is in the [Developer Guide](https://manimgx.academa.ai/developer-guide/).

## Issues

Everything starts as an [issue](https://github.com/academa-labs/manimgx/issues/new/choose):
bugs, feature requests, problems in the docs, and questions. Search the existing issues first,
then pick the form that fits.

To report a security vulnerability, don't open an issue: follow the
[security policy](https://github.com/academa-labs/manimgx/blob/main/.github/SECURITY.md).

## Before you start

For anything larger than a small fix, open an issue first and describe what you want to
change. Agreeing on the approach before you write the code saves you work.

ManimGX takes its API from [Manim Community Edition](https://www.manim.community): the same
names and parameters. It does not take CE's behavior. What a scene means (its timing, its
geometry, how it looks) is decided on its own merits, so "Manim CE does it this way" is a
reason to look closely, not a reason to change ManimGX.

## Making a change

The Developer Guide has everything a change needs:

- [Setup](https://manimgx.academa.ai/developer-guide/): the tools, the system libraries and
  the GPU, and the environment, from a clone to a passing test run.
- [Project management](https://manimgx.academa.ai/developer-guide/project-management/): the
  configuration, the checks, and the rules for typing and formatting.
- [Understanding ManimGX](https://manimgx.academa.ai/developer-guide/understanding-manimgx/)
  and [the engine](https://manimgx.academa.ai/developer-guide/engine/): how a scene becomes a
  video.
- [Testing](https://manimgx.academa.ai/developer-guide/testing/): the tests, the integration
  corpus and its review panel.
- [Documentation](https://manimgx.academa.ai/developer-guide/documentation/): the docs site,
  the docstrings its reference is generated from, and the changelog.

## Pull requests

- Keep a pull request to one change, and link the issue it resolves.
- A fix or a feature comes with a test that shows it. After the first release, a user-visible
  change also gets a line under "Unreleased" in the changelog.
- Before you open it, run `just check` and `just test`, and say in the pull request what you
  ran and what you looked at. If the change could slow rendering down, run `just bench main`
  and put its table in it.
- Pull requests are squash-merged, and the title becomes the commit message. Write it as one
  plain sentence that says what changes, like the rest of `git log --oneline`.
- A maintainer reviews every pull request. They may ask for changes, or close a pull request
  that doesn't fit the project.

## Use of AI

AI tools are welcome, and you are still the author:

- Understand every line you submit, run it, and be ready to explain it in review.
- Say in the pull request which tools you used, and for what.
- Don't let an agent act for you: an agent may not open issues or pull requests, or comment,
  on its own.

## License

By contributing, you agree that your contributions are licensed under ManimGX's
[MIT License](https://github.com/academa-labs/manimgx/blob/main/LICENSE).

## Code of conduct

Everyone taking part in ManimGX follows its
[code of conduct](https://github.com/academa-labs/manimgx/blob/main/.github/CODE_OF_CONDUCT.md).
