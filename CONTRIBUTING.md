# Contributing to Photo Scoring

## Branching Strategy

We use a simplified Git Flow workflow:

```
master (production)
   ↑
   PR (with CI checks)
   ↑
develop (integration)
   ↑
   PR (with CI checks)
   ↑
feature/xxx or fix/xxx (your work)
```

### Branches

| Branch | Purpose |
|--------|---------|
| `master` | Production-ready code, always stable |
| `develop` | Integration branch for features |
| `feature/*` | New features (branch from develop) |
| `fix/*` | Bug fixes (branch from develop) |
| `hotfix/*` | Urgent production fixes (branch from master) |

## Development Workflow

### 1. Start a New Feature

```bash
# Ensure you're on develop and up to date
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Work on Your Feature

```bash
# Make changes, commit frequently
git add .
git commit -m "feat: description of change"

# Push to remote
git push -u origin feature/your-feature-name
```

### 3. Create Pull Request

```bash
# Create PR to develop
gh pr create --base develop --title "feat: your feature" --body "Description"
```

Or visit: https://github.com/francisbrero/photo-scoring/compare

### 4. After PR is Merged

```bash
# Clean up local branch
git checkout develop
git pull origin develop
git branch -d feature/your-feature-name
```

## Commit Message Convention

Use conventional commits:

```
feat: add new feature
fix: fix a bug
docs: update documentation
refactor: code refactoring
test: add or update tests
chore: maintenance tasks
```

## Pull Request Checklist

- [ ] Tests pass (`/test`)
- [ ] Code is formatted (`/lint` or `/fix`)
- [ ] PR description explains the change
- [ ] Related issues are linked

## CI/CD

Pull requests trigger:
- **Test job**: pytest with coverage
- **Lint job**: ruff format and lint checks

Both must pass before merging to master.

## Quick Commands

| Command | Description |
|---------|-------------|
| `/test` | Run tests with coverage |
| `/lint` | Check code style |
| `/fix` | Auto-fix code style |
| `/score <dir>` | Score photos |
| `/viewer <dir>` | Start web viewer |
