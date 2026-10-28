# Privacy and security

Conversation exports can contain source code, credentials, file paths, identities, tool results,
and attachment data. Treat **all generated exports and reports as private**, even when T3 imports
only their visible text. Never attach them to public issues or commit them to this repository.

The exporter contacts only loopback. It obtains the local Antigravity service token in memory and
does not log it. Never run the internal endpoint-discovery helper directly in a recorded terminal.
No tool here needs a GitHub token, Google password, or Google refresh token.

The tools refuse to put generated exports in this repository. `.gitignore` and the indexed-file
audit provide additional guardrails. They cannot recognize every secret or personal fact. Review
the complete staged diff before publishing, including Git author/committer metadata.

For a bug report, provide the pinned revision, OS/architecture, tool versions, and sanitized counts
or error categories. Reproduce with a synthetic fixture. Do not send process command lines,
database files, environment dumps, raw service responses, or screenshots of private chats.

If a credential is exposed, revoke or rotate it at its provider. Deleting a public commit does not
make an exposed credential safe. For a vulnerability in this project, use the repository's private
security-reporting feature when available. Do not post exploit data or secrets in a public issue.
