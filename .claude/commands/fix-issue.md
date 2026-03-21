# Fix GitHub Issue

Fetch and implement GitHub issue #$ARGUMENTS

## Workflow

### Step 1: Fetch Issue
Use `gh issue view $ARGUMENTS` to get issue details including:
- Title, description, labels
- Acceptance criteria
- Dependencies and references

### Step 2: Create Branch
Create a branch based on issue labels:
- `feature/issue-<number>` for enhancements
- `bugfix/issue-<number>` for bugs
- `chore/issue-<number>` for maintenance tasks
- `refactor/issue-<number>` for code refactoring
- `test/issue-<number>` for testing
- `docs/issue-<number>` for documentation
- `perf/issue-<number>` for performance improvements
- `issue/issue-<number>` for general issues (default)

### Step 3: Ensure Dependencies
**IMPORTANT**: Before running any commands, ensure dependencies are installed:
```bash
uv sync --dev
```

This is **required** because:
- Test and lint commands require dev dependencies
- Without this step, `pytest`, `ruff`, etc. will fail

### Step 4: Research & Plan (MANDATORY — do NOT skip)
1. Analyze issue requirements thoroughly
2. Search codebase for affected files using Grep/Glob
3. Check relevant skills in `.claude/skills/` for patterns:
   - `technical/` - Architecture and implementation details
   - `runbooks/` - Step-by-step procedures
   - `reference/` - Quick lookup information
4. Identify dependencies and integration points
5. Create implementation plan covering:
   - Files to change and why
   - Summary of each change
   - Any risks or trade-offs
6. Use `EnterPlanMode` to present the plan to the user

**MANDATORY**: You MUST present a plan and receive explicit user approval before writing any code or making any changes. This applies to ALL issues regardless of size or perceived simplicity. Do NOT skip this step even for one-line fixes. No exceptions.

### Step 5: Implementation (only after plan is approved)
For each phase:
1. Implement changes following project patterns:
   - Check existing code in `photo_score/` for conventions
   - Reference relevant skills during implementation
2. Run `/lint` after each significant change
3. Keep changes focused and minimal

### Step 6: Testing
1. Run unit tests: `uv run pytest -v`
2. Run linting: `uv run ruff check . && uv run ruff format --check .`
3. Fix any issues before proceeding

Use `/test` skill for running tests with coverage.

### Step 7: Finalization
1. Run full checks: `uv run pytest -v && uv run ruff check .`
2. Create commit following guidelines:
   - Clear, descriptive commit message
   - Reference issue number: "Closes #$ARGUMENTS"
3. Push branch and create PR
4. Link PR to issue

## Guidelines
- Reference relevant skills in `.claude/skills/` during implementation
- Run `/lint` frequently during development
- Use `/test` to verify changes don't break existing functionality
- Keep changes minimal and focused on the issue

## Key Skills Reference
- `/score` - Score photos workflow
- `/test` - Run test suite
- `/lint` - Check code style
- `/fix` - Auto-fix code style issues
- `/costs` - Estimate API costs

## Project Architecture
See CLAUDE.md for:
- Project structure overview
- CLI commands
- Environment variables
- Architecture notes (attributes, scoring, caching)
