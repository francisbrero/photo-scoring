# Skills

Production-tested skills for Claude Code that auto-activate based on context using Anthropic's official skill format.

---

## Directory Structure

```
.claude/skills/
├── technical/              # Technical domain skills (5)
│   ├── openrouter-client.md
│   ├── scoring-pipeline.md
│   ├── prompts-engineering.md
│   ├── sqlite-cache.md
│   └── web-viewer.md
├── runbooks/               # Step-by-step guides (5)
│   ├── score-photos.md
│   ├── run-tests.md
│   ├── add-new-model.md
│   ├── modify-prompts.md
│   └── clear-cache.md
└── reference/              # Documentation references (3)
    ├── cost-reference.md
    ├── project-structure.md
    └── github-issues.md
```

---

## How Skills Work

1. **Automatic activation**: Skills activate based on file patterns (globs) or descriptions
2. **Context injection**: When activated, skill content is added to Claude's context
3. **Progressive disclosure**: Skills provide quick reference with links to full documentation

---

## Skill Format

Each skill uses this format:

```markdown
---
description: Brief description for skill matching
globs:
  - "src/server/db/**/*.ts"
alwaysApply: false
---

# Skill Name

## Overview
Brief overview of when to use this skill.

## Key Patterns
Code examples and patterns.

## Resources
Links to detailed documentation.
```

---

## Adding a New Skill

1. **Choose category**: `technical/`, `runbooks/`, or `reference/`
2. **Create file**: `[skill-name].md`
3. **Add frontmatter**: description, globs, alwaysApply
4. **Write content**: Overview, patterns, resources

---

## Skill Categories

### Technical Skills
Domain-specific knowledge about the codebase:
- OpenRouter API client patterns
- Scoring pipeline architecture
- Prompt engineering guidelines
- Cache layer operations
- Web viewer components

### Runbooks
Step-by-step guides for common tasks:
- Scoring photos
- Running tests
- Adding new models
- Modifying prompts
- Cache management

### Reference
Quick-lookup documentation:
- Cost estimates and pricing
- Project structure
- GitHub issues and roadmap

---

## Reference

- Based on Anthropic's official skill format
- [Claude Code Infrastructure Showcase](https://github.com/diet103/claude-code-infrastructure-showcase)
