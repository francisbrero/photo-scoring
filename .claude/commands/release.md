---
description: Release a new version of the Photo Scorer desktop app
argument-hint: [patch|minor|major]
allowed-tools: Bash(git:*), Bash(gh:*), Read, Edit
---

# Release Desktop App

Create a new release of the Photo Scorer desktop app. This command:
1. Increments the version number in package.json
2. Commits the version bump
3. Creates and pushes a git tag to trigger the release workflow

## Usage

```
/release           # Bump patch version (0.2.0 -> 0.2.1)
/release patch     # Bump patch version (0.2.0 -> 0.2.1)
/release minor     # Bump minor version (0.2.0 -> 0.3.0)
/release major     # Bump major version (0.2.0 -> 1.0.0)
```

## Steps

1. Read the current version from `packages/desktop/package.json`
2. Parse the version and increment based on the argument (default: patch)
3. Update package.json with the new version
4. Commit with message "Bump desktop app version to X.Y.Z"
5. Create annotated tag `desktop-vX.Y.Z`
6. Push commit and tag to origin
7. Report the release URL for monitoring

## Version Increment Rules

- **patch** (default): Bug fixes, minor improvements, naming changes
- **minor**: New features, significant improvements
- **major**: Breaking changes, major rewrites

## Important

- Always use this command when shipping updates, even for minor changes
- The tag push triggers the GitHub Actions workflow that builds and publishes the release
- Monitor the release at: https://github.com/francisbrero/photo-scoring/actions

## Example Output

```
Current version: 0.2.0
New version: 0.2.1
Committed: Bump desktop app version to 0.2.1
Tag created: desktop-v0.2.1
Pushed to origin

Release workflow started: https://github.com/francisbrero/photo-scoring/actions
```
