---
description: GitHub issues reference, roadmap and backlog
globs: []
alwaysApply: false
---

# GitHub Issues Reference

## Milestone: Public App Launch

Issues required to expose photo-scoring as a public web application.

| # | Title | Status |
|---|-------|--------|
| 4 | Add user authentication | Open |
| 5 | Add payment system for credits | Open |
| 6 | Add free trial with 10 photo credits | Open |
| 7 | Define picture storage strategy | Open |
| 8 | Add settings page | Open |
| 9 | Create picture management features | Open |
| 19 | Create landing page | Open |
| 20 | Add privacy policy and terms of service | Open |
| 21 | Add analytics tracking | Open |

## Infrastructure & DevOps

| # | Title | Priority |
|---|-------|----------|
| 1 | Clean up CSV files | Low |
| 2 | Host app on Vercel | Medium |
| 22 | Code review and cleanup | Medium |

## Performance & Cost

| # | Title | Priority |
|---|-------|----------|
| 3 | Support local models for inference | High |
| 23 | Add pyiqa as local scoring backend | High |
| 25 | Add hybrid scoring mode | High |

## Features

| # | Title | Priority |
|---|-------|----------|
| 10 | Add rate limiting and error handling UI | Medium |
| 11 | Add batch processing progress indicator | Medium |
| 12 | Add export options beyond CSV | Medium |
| 15 | Add photo comparison mode | Medium |
| 16 | Add batch actions in viewer | Medium |
| 17 | Add user score calibration | High |
| 18 | Add before/after editing comparison | Low |
| 24 | Add Lightroom XMP sidecar export | High |
| 26 | Add score confidence/distribution | Medium |

## Technical Debt

| # | Title | Priority |
|---|-------|----------|
| 13 | Add comprehensive test coverage | Medium |
| 14 | Add type hints and documentation | Low |

## Research

| # | Title | Status |
|---|-------|--------|
| 27 | Study Aftershoot UX for preference learning | Open |

## Quick Links

- [All Issues](https://github.com/francisbrero/photo-scoring/issues)
- [Public App Launch Milestone](https://github.com/francisbrero/photo-scoring/milestone/1)

## Creating New Issues

```bash
gh issue create --title "Issue title" --body "Description"

# With milestone
gh issue create --title "Title" --milestone "Public App Launch" --body "..."
```
