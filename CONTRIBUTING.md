# Contributing

Keep changes portable and fixtures synthetic. Do not copy production transcripts, installed app
files, credentials, or generated reports into this repository. Preserve upstream license notices.

1. Prepare the pinned checkout using `scripts/prepare_checkout.py`.
2. Read that checkout's `AGENTS.md` and follow its focused validation requirements.
3. Make and test source changes there. Update the patch using repository-relative paths only;
   include newly added files, and omit build outputs and local configuration.
4. Run `python -m unittest discover -s tests -v` here and the affected T3 tests/typechecks there.
5. Verify the patch applies to a fresh checkout of `UPSTREAM_REVISION`.
6. Stage only intended source files, run `python scripts/verify-public.py`, and inspect the entire
   staged diff. Use a GitHub no-reply address if you do not want to publish your personal email.

When changing the pinned revision, update the compatibility documentation and version guards,
rebuild against the matching installed release, and validate installation and rollback on a
disposable copy. Never test a development server against a real user's T3 data directory.

Do not claim a platform or native conversation-resume path is supported without testing it.
