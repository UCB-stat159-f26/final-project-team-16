# Contributing to the STAT 159 final project

## Pick a task

Check open issues and PRs before starting. Claim the issue, identify the research question or shared deliverable, and name one result a teammate can verify. Record dependencies, such as the CFS snapshot or the reviewed event dates, in the issue. Link the definition and codebook entries used by the analysis.

## Work on a branch

Start a task branch from an up-to-date main. Use a type/content branch name such as `analysis/calendar`. Stage the intended paths and inspect the staged diff before committing. Each notebook has one owner. Only the owner edits it. Teammates suggest changes through pull request reviews. When two notebooks need the same filtering rule, put it in a documented function both can import.

## Document and verify changes

- Give each new or substantially changed script a short description of its purpose, inputs and outputs. Document each function's purpose, parameters and types, return value, and relevant edge cases.
- Explain decisions that affect counts, such as deduplicating stop IDs or including days with zero calls. Update the shared definitions and codebook alongside changes in measurement.
- For a data update, record the source, snapshot date, observation unit, coverage and exclusions. Regenerate affected outputs and update the report from those outputs.
- Run the relevant scripts, notebooks or tests from the repository root. In the PR, give the exact command and a check another person can repeat. For a documentation change, inspect the rendered Markdown and check paths and links.

## Request review and merge

Open a PR into main and complete the template. Use Refs #N for partial work and Closes #N when merging completes the issue. Replace N with the actual issue number.

| Author or deliverable | Reviewer |
| --- | --- |
| John's PRs | Minchee |
| Minchee's PRs | John |
| Winny's A1 trends | John |
| Winny's A8 noise hotspots | Minchee |
| Licenses, codebook and calendar dates | Winny checks licenses, reads the codebook and verifies calendar dates against the cited sources. For John's PRs, request Minchee's review as well. |

The reviewer checks the issue criteria and reproduces a key result or verifies a source. Resolve comments, rerun the affected checks and merge after approval. Record remaining work in the issue. Keep the AI-use log current and write individual reflections in the contributor's own words.
