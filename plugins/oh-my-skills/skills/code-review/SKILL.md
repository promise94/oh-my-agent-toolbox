---
name: code-review
description: |
  Code review a GitLab merge request using multiple specialized agents with confidence-based scoring.
  Use when: user wants to review a GitLab merge request, or says /code-review.
  Adapted from the official code-review plugin for GitHub, targeting a configured self-hosted GitLab instance.
allowed-tools: Bash(glab mr view:*), Bash(glab mr diff:*), Bash(glab mr note:*), Bash(glab mr list:*), Bash(glab issue view:*), Bash(glab issue list:*), Bash(git log:*), Bash(git blame:*)
license: Apache-2.0
metadata:
  version: "1.0.1"
  based-on: "code-review by Anthropic"
disable-model-invocation: false
---

# GitLab Code Review

Provide a code review for the given merge request.

To do this, follow these steps precisely:

1. Use a lightweight triage agent to check if the merge request (a) is closed/merged, (b) is a draft, (c) does not need a code review (eg. because it is an automated merge request, or is very simple and obviously ok), or (d) already has a code review from you from earlier. If so, do not proceed.
2. Use another lightweight context-discovery agent to give you a list of file paths to (but not the contents of):
   - any relevant CLAUDE.md files from the codebase: the root CLAUDE.md file (if one exists), as well as any CLAUDE.md files in the directories whose files the merge request modified
   - any existing project documentation that may be affected by the merge request, such as README.md, docs/, API docs, data model docs, runbooks, or test strategy docs
3. Use a lightweight summary agent to view the merge request, and ask the agent to return a summary of the change
4. Then, launch 5 parallel independent review agents to review the change. The agents should do the following, then return a list of issues and the reason each issue was flagged (eg. CLAUDE.md adherence, bug, historical git context, etc.):
   a. Agent #1: Audit the changes to make sure they compily with the CLAUDE.md. Note that CLAUDE.md is guidance for Claude as it writes code, so not all instructions will be applicable during code review.
   b. Agent #2: Read the file changes in the merge request, then do a shallow scan for obvious bugs. Avoid reading extra context beyond the changes, focusing just on the changes themselves. Focus on large bugs, and avoid small issues and nitpicks. Ignore likely false positives.
   c. Agent #3: Read the git blame and history of the code modified, to identify any bugs in light of that historical context
   d. Agent #4: Read previous merge requests that touched these files (use `git log` to find them), and check for any comments on those merge requests that may also apply to the current merge request.
   e. Agent #5: Read code comments in the modified files, and make sure the changes in the merge request comply with any guidance in the comments.

   Review agents that read project context should also check project documentation synchronization when documentation is part of the repository workflow. Agent #2 remains a shallow diff-only bug scan and should not expand into documentation discovery. Flag missing documentation updates only when all are true:
   - the MR changes public behavior, APIs, data models, commands, environment variables, deployment/runtime behavior, test strategy, or important workflow rules;
   - the repository already has relevant documentation from step 2;
   - stale docs would mislead future development, testing, debugging, deployment, or AI-assisted workflows.
   Do not flag trivial implementation-only changes, wording-only differences, or repositories without a relevant documentation convention.
5. For each issue found in #4, launch a parallel confidence-scoring agent that takes the MR, issue description, and list of CLAUDE.md files (from step 2), and returns a score to indicate the agent's level of confidence for whether the issue is real or false positive. To do that, the agent should score each issue on a scale from 0-100, indicating its level of confidence. For issues that were flagged due to CLAUDE.md instructions, the agent should double check that the CLAUDE.md actually calls out that issue specifically. The scale is (give this rubric to the agent verbatim):
   a. 0: Not confident at all. This is a false positive that doesn't stand up to light scrutiny, or is a pre-existing issue.
   b. 25: Somewhat confident. This might be a real issue, but may also be a false positive. The agent wasn't able to verify that it's a real issue. If the issue is stylistic, it is one that was not explicitly called out in the relevant CLAUDE.md.
   c. 50: Moderately confident. The agent was able to verify this is a real issue, but it might be a nitpick or not happen very often in practice. Relative to the rest of the MR, it's not very important.
   d. 75: Highly confident. The agent double checked the issue, and verified that it is very likely it is a real issue that will be hit in practice. The existing approach in the MR is insufficient. The issue is very important and will directly impact the code's functionality, or it is an issue that is directly mentioned in the relevant CLAUDE.md.
   e. 100: Absolutely certain. The agent double checked the issue, and confirmed that it is definitely a real issue, that will happen frequently in practice. The evidence directly confirms this.
6. Present all review results and scoring results back to the user in the main conversation before filtering. Include: each independent review agent's issues or "no issues", each scored candidate issue with score/evidence, and which issues will or will not be posted.
7. Filter out any issues with a score less than 50. If there are no issues that meet this criteria, continue to the final comment with the "No issues found" format.
8. Use a lightweight triage agent to repeat the eligibility check from #1, to make sure that the merge request is still eligible for code review.
9. Finally, use the `glab mr note` bash command to comment back on the merge request with the result. When writing your comment, keep in mind to:
   a. Keep your output brief
   b. Avoid emojis
   c. Link and cite relevant code, files, and URLs

Examples of false positives, for steps 4 and 5:

- Pre-existing issues
- Something that looks like a bug but is not actually a bug
- Pedantic nitpicks that a senior engineer wouldn't call out
- Issues that a linter, typechecker, or compiler would catch (eg. missing or incorrect imports, type errors, broken tests, formatting issues, pedantic style issues like newlines). No need to run these build steps yourself -- it is safe to assume that they will be run separately as part of CI.
- General code quality issues (eg. lack of test coverage, general security issues, poor documentation), unless explicitly required in CLAUDE.md or the MR leaves existing project documentation stale for changed behavior that the repository docs already cover
- Issues that are called out in CLAUDE.md, but explicitly silenced in the code (eg. due to a lint ignore comment)
- Changes in functionality that are likely intentional or are directly related to the broader change
- Real issues, but on lines that the user did not modify in their merge request

Notes:

- Do not check build signal or attempt to build or typecheck the app. These will run separately, and are not relevant to your code review.
- Use `glab` to interact with GitLab (eg. to fetch a merge request, or to create comments), rather than web fetch
- **GitLab version compatibility:** The glab CLI (latest version) may crash with older GitLab CE instances (e.g., nil pointer dereference in `glab mr list`). To handle this gracefully:
  1. First try the standard `glab` subcommand (e.g., `glab mr list`, `glab mr view`).
  2. If it crashes or errors, fall back to `glab api` with the raw REST API endpoint. Common fallbacks:
     - List MRs assigned to me: `glab api "merge_requests?scope=assigned_to_me&state=opened"`
     - List MRs for review: `glab api "merge_requests?scope=review_requested_from_me&state=opened"`
     - View MR details: `glab api "projects/<url-encoded-project>/merge_requests/<iid>"`
     - Get MR changes: `glab api "projects/<url-encoded-project>/merge_requests/<iid>/changes"`
     - Get MR notes: `glab api "projects/<url-encoded-project>/merge_requests/<iid>/notes"`
  3. Commands that are known to work reliably even on older GitLab: `glab mr diff`, `glab mr note`, `glab mr view`.
- Make a todo list first
- You must cite and link each bug (eg. if referring to a CLAUDE.md, you must link it)
- For your final comment, follow the following format precisely (assuming for this example that you found 3 issues):

---

### Code review

Found 3 issues:

1. <brief description of bug> (CLAUDE.md says "<...>")

<link to file and line with branch name + line range for context, eg. https://<gitlab-host>/group/project/blob/feat/some_branch/README.md#L13-17>

2. <brief description of bug> (some/other/CLAUDE.md says "<...>")

<link to file and line with branch name + line range for context>

3. <brief description of bug> (bug due to <file and code snippet>)

<link to file and line with branch name + line range for context>

Generated with Claude Code

---

- Or, if you found no issues:

---

### Code review

No issues found. Checked for bugs and CLAUDE.md compliance.

Generated with Claude Code

- When linking to code, follow the following format precisely, otherwise the Markdown preview won't render correctly: https://<gitlab-host>/group/project/blob/feat/some_branch/package.json#L10-15
  - Use the URL format supported by the configured GitLab instance. For older GitLab CE instances, URLs may omit `/-/` and use `/blob/` directly.
    - CORRECT: `https://<gitlab-host>/<group>/<project>/blob/<ref>/<path>#L<start>-<end>`
    - WRONG:   `https://<gitlab-host>/<group>/<project>/-/blob/<ref>/<path>#L<start>-<end>` when the configured instance uses the older format
  - For `<ref>`, prefer using the MR source branch name (e.g., `feat/r20260123_refactor`) instead of commit SHA, as branch names work more reliably on this GitLab version.
  - You must provide the full ref. Commands like `https://<gitlab-host>/group/project/blob/$(git rev-parse HEAD)/foo/bar` will not work, since your comment will be directly rendered in Markdown.
  - Project path must match the project you're code reviewing
  - # sign after the file name
  - Line range format is L[start]-[end] (GitLab format, no L prefix on end line)
  - Provide at least 1 line of context before and after, centered on the line you are commenting about (eg. if you are commenting about lines 5-6, you should link to `L4-7`)
