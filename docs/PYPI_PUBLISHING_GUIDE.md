# 📦 PyPI Publishing Guide

Complete guide for publishing SSH MCP Tools to PyPI using GitHub Actions and trusted publishing.

## 🎯 Prerequisites

### 1. PyPI Account Setup

1. Create accounts on both [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org)
1. Enable 2FA on both accounts
1. Note your usernames for both platforms

### 2. GitHub Repository Setup

1. Ensure your repository is public (required for trusted publishing)
1. Repository must be named exactly as specified in PyPI project settings
1. Verify repository URL matches the one in `pyproject.toml`

## 🔐 Configure Trusted Publishing

### 1. PyPI Trusted Publishing Setup

#### For Production PyPI:

1. Go to [PyPI](https://pypi.org) and log in
1. Navigate to "Your projects" → "Manage" (or create new project)
1. Go to "Settings" → "Publishing"
1. Click "Add a new publisher"
1. Fill in the details:
   - **Repository name**: `enwaiax/shuttle`
   - **Workflow filename**: `publish-to-pypi.yml`
   - **Environment name**: `pypi`

#### For TestPyPI:

1. Go to [TestPyPI](https://test.pypi.org) and log in
1. Follow the same steps as above but use:
   - **Environment name**: `testpypi`

### 2. GitHub Environment Setup

1. Go to your GitHub repository
1. Navigate to "Settings" → "Environments"
1. Create two environments:

#### Environment: `pypi`

- **Name**: `pypi`
- **Protection rules**:
  - ✅ Required reviewers (optional, for extra safety)
  - ✅ Wait timer (optional, for staged releases)

#### Environment: `testpypi`

- **Name**: `testpypi`
- **Protection rules**: None required for testing

## 🚀 Publishing Process

### Option 1: Automated Release (Recommended)

#### Step 1: Prepare Release

```bash
# Update version in pyproject.toml
sed -i 's/version = "[^"]*"/version = "1.0.0"/' pyproject.toml

# Update CHANGELOG.md
# Add release notes under ## [Unreleased] section

# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: prepare release v1.0.0"
git push origin main
```

#### Step 2: Create Release Tag

```bash
# Create and push tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

#### Step 3: Create GitHub Release

1. Go to [Releases](https://github.com/enwaiax/shuttle/releases)
1. Click "Create a new release"
1. Select tag `v1.0.0`
1. Add release title: `SSH MCP Tools v1.0.0`
1. Add release notes from CHANGELOG.md
1. Click "Publish release"

This triggers the automated workflow that will:

1. ✅ Run comprehensive tests
1. ✅ Build the package
1. ✅ Publish to TestPyPI
1. ✅ Publish to PyPI (production)

### Option 2: Manual Workflow Trigger

1. Go to "Actions" tab in your GitHub repository
1. Select "Release" workflow
1. Click "Run workflow"
1. Enter version number (e.g., `1.0.0`)
1. Select release type (patch/minor/major)
1. Click "Run workflow"

### Option 3: Local Publishing (Not Recommended)

```bash
# Install build tools
uv sync --dev

# Build package
uv build

# Check package
uv run twine check dist/*

# Upload to TestPyPI first
uv run twine upload --repository testpypi dist/*

# If successful, upload to PyPI
uv run twine upload dist/*
```

## ✅ Verification

### 1. Check TestPyPI

- Visit: https://test.pypi.org/project/shuttle-mcp/
- Verify package information and files

### 2. Test Installation from TestPyPI

```bash
uv pip install --index-url https://test.pypi.org/simple/ shuttle-mcp
shuttle --version
```

### 3. Check PyPI

- Visit: https://pypi.org/project/shuttle-mcp/
- Verify package is available

### 4. Test Production Installation

```bash
uv pip install shuttle-mcp
shuttle --help
```

## 🔍 Monitoring and Maintenance

### Download Statistics

- Check PyPI project page for download statistics
- Use tools like [pypistats](https://pypistats.org/) for detailed analytics

### Version Management

- Follow [Semantic Versioning](https://semver.org/)
- Update `CHANGELOG.md` for each release
- Tag releases consistently (`v1.0.0`, `v1.1.0`, etc.)

### Security Updates

- Monitor dependencies for security vulnerabilities
- Update dependencies regularly
- Use `uv sync --upgrade` to update dependencies

## 🛠️ Troubleshooting

### Common Issues

#### 1. Trusted Publishing Not Working

```
Error: The user 'username' isn't allowed to upload to project 'shuttle-mcp'
```

**Solution**:

- Verify trusted publishing is configured correctly on PyPI
- Check that repository name, workflow file, and environment name match exactly
- Ensure the GitHub environment exists and has proper permissions

#### 2. Package Already Exists

```
ERROR: File already exists
```

**Solution**:

- You cannot overwrite existing versions on PyPI
- Bump the version number in `pyproject.toml`
- Create a new release

#### 3. Test Failures in CI

```
Tests failed during GitHub Actions workflow
```

**Solution**:

- Check the Actions tab for detailed error logs
- Fix failing tests locally first
- Push fixes and re-trigger the workflow

#### 4. Build Failures

```
Package build failed
```

**Solution**:

- Check `pyproject.toml` for syntax errors
- Ensure all required files are included
- Test build locally: `uv build`

### Debug Commands

```bash
# Validate package structure
uv run python -m tarfile -l dist/*.tar.gz

# Check package metadata
uv run python -c "import importlib.metadata; print(importlib.metadata.metadata('shuttle-mcp'))"

# Test package installation
uv pip install dist/*.whl
uv run python -c "import python_ssh_mcp; print('Import successful')"
```

## 📋 Pre-Release Checklist

- [ ] All tests pass locally: `uv run pytest`
- [ ] Code quality checks pass: `uv run ruff check`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] Documentation is updated
- [ ] `CHANGELOG.md` is updated
- [ ] Version bumped in `pyproject.toml`
- [ ] Package builds successfully: `uv build`
- [ ] Trusted publishing is configured on PyPI/TestPyPI
- [ ] GitHub environments exist and are configured

## 🎉 Success Metrics

After successful publishing:

- ✅ Package appears on PyPI
- ✅ Installation works: `uv pip install shuttle-mcp`
- ✅ CLI works: `shuttle --version`
- ✅ Import works: `python -c "import python_ssh_mcp"`
- ✅ All functionality operational

## 📞 Getting Help

- **PyPI Issues**: [PyPI Help](https://pypi.org/help/)
- **GitHub Actions**: [GitHub Actions Documentation](https://docs.github.com/en/actions)
- **Trusted Publishing**: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- **Project Issues**: [GitHub Issues](https://github.com/enwaiax/shuttle/issues)

______________________________________________________________________

*Ready to publish? Follow the automated release process for the smoothest experience!*
