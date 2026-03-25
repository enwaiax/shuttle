# 🚀 Release Process Guide

This document outlines the release process for publishing SSH MCP Tools to PyPI.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Release Types](#release-types)
- [Step-by-Step Release Process](#step-by-step-release-process)
- [Automated Release Workflow](#automated-release-workflow)
- [Manual Release Process](#manual-release-process)
- [Post-Release Tasks](#post-release-tasks)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The project uses automated GitHub Actions workflows to:

1. Run comprehensive tests across multiple platforms
1. Build the package
1. Publish to TestPyPI for validation
1. Publish to PyPI for production release

## ✅ Prerequisites

Before releasing, ensure:

- [ ] All tests pass locally: `uv run pytest`
- [ ] Code quality checks pass: `uv run ruff check` and `uv run ruff format --check`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated with new features/fixes
- [ ] Version number is bumped in `pyproject.toml`

## 📦 Release Types

### Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

### Release Channels

1. **Development**: Direct pushes to `main` trigger tests
1. **Testing**: TestPyPI for pre-release validation
1. **Production**: PyPI for stable releases

## 🚀 Step-by-Step Release Process

### 1. Prepare the Release

```bash
# Ensure you're on the main branch and up to date
git checkout main
git pull origin main

# Update version in pyproject.toml
# Edit the version field: version = "x.y.z"

# Update CHANGELOG.md with release notes
# Document new features, bug fixes, and breaking changes

# Commit version bump
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to x.y.z"
git push origin main
```

### 2. Create and Push Release Tag

```bash
# Create a version tag
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push the tag to GitHub
git push origin v1.0.0
```

### 3. Create GitHub Release

1. Go to [GitHub Releases](https://github.com/enwaiax/shuttle/releases)
1. Click "Create a new release"
1. Select the tag you just created
1. Fill in release title: `v1.0.0`
1. Add release notes from CHANGELOG.md
1. Check "Set as the latest release" for stable releases
1. Click "Publish release"

## 🤖 Automated Release Workflow

When you create a GitHub release or push a version tag, the workflow automatically:

### Phase 1: Testing

- Runs tests on Ubuntu, Windows, and macOS
- Performs code quality checks
- Runs type checking
- Generates coverage reports

### Phase 2: Building

- Builds the package using `uv build`
- Creates both wheel (.whl) and source (.tar.gz) distributions

### Phase 3: TestPyPI Publication

- Publishes to TestPyPI for validation
- URL: https://test.pypi.org/p/fastmcp-ssh-server

### Phase 4: PyPI Publication

- Publishes to production PyPI
- URL: https://pypi.org/p/fastmcp-ssh-server

## 🔧 Manual Release Process

If you need to release manually:

```bash
# Install build dependencies
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Build the package
uv build

# Check the built package
uv run twine check dist/*

# Upload to TestPyPI (optional)
uv run twine upload --repository testpypi dist/*

# Upload to PyPI
uv run twine upload dist/*
```

## 📋 Post-Release Tasks

After a successful release:

1. **Verify Installation**:

   ```bash
   uv pip install shuttle-mcp
   fastmcp-ssh-server --help
   ```

1. **Update Documentation**:

   - Update installation instructions
   - Update version numbers in examples
   - Update compatibility matrices

1. **Announce the Release**:

   - Update project README if needed
   - Share on relevant communities
   - Update project status

1. **Monitor**:

   - Check PyPI download statistics
   - Monitor for user feedback and issues
   - Watch for compatibility reports

## 🛠️ Troubleshooting

### Common Issues

#### 1. Version Already Exists on PyPI

```
ERROR: File already exists
```

**Solution**: Bump the version number in `pyproject.toml` and create a new release.

#### 2. Test Failures

```
Tests failed in CI/CD pipeline
```

**Solution**: Fix the failing tests locally and push the fixes before releasing.

#### 3. Build Failures

```
Package build failed
```

**Solution**:

- Check `pyproject.toml` for syntax errors
- Ensure all required files are included
- Verify dependencies are correctly specified

#### 4. Authentication Issues

```
Authentication failed for PyPI
```

**Solution**:

- Ensure GitHub repository has proper PyPI trusted publishing configured
- Check that the repository name matches PyPI project name

### Debugging Commands

```bash
# Check package metadata
uv run python -c "import importlib.metadata; print(importlib.metadata.metadata('fastmcp-ssh-server'))"

# Validate package structure
uv run python -m tarfile -l dist/*.tar.gz

# Test import locally
uv run python -c "from ssh_mcp import cli; print('Import successful')"
```

## 🔐 Security Considerations

- Never commit PyPI tokens to the repository
- Use GitHub's trusted publishing for secure authentication
- Verify package contents before releasing
- Monitor for security vulnerabilities in dependencies

## 📊 Release Checklist Template

```markdown
## Release vX.Y.Z Checklist

### Pre-Release
- [ ] All tests pass locally
- [ ] Code quality checks pass
- [ ] Version bumped in pyproject.toml
- [ ] CHANGELOG.md updated
- [ ] Documentation updated
- [ ] Breaking changes documented

### Release Process
- [ ] Version tag created and pushed
- [ ] GitHub release created
- [ ] CI/CD pipeline passed
- [ ] TestPyPI publication successful
- [ ] PyPI publication successful

### Post-Release
- [ ] Installation verified
- [ ] Documentation updated
- [ ] Release announced
- [ ] Monitoring setup
```

## 📈 Version History

Track your releases:

| Version | Date       | Type    | Description                    |
| ------- | ---------- | ------- | ------------------------------ |
| v0.1.0  | 2025-08-06 | Initial | First release with v1/v2 tools |
|         |            |         |                                |

______________________________________________________________________

*This guide ensures consistent, reliable releases for the SSH MCP Tools project.*
