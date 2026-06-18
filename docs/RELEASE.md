# Release Process

This document defines the release process for the WMS MCP Server project.

## Table of Contents

- [Versioning](#versioning)
- [Release Types](#release-types)
- [Release Process](#release-process)
- [Pre-Release Checklist](#pre-release-checklist)
- [Release Steps](#release-steps)
- [Post-Release Steps](#post-release-steps)
- [Rollback Procedure](#rollback-procedure)
- [Release Notes](#release-notes)

## Versioning

We follow **Semantic Versioning** (SemVer) for version numbers:

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

### Examples

- `1.0.0` → `1.1.0`: New feature (minor)
- `1.1.0` → `1.1.1`: Bug fix (patch)
- `1.1.1` → `2.0.0`: Breaking change (major)

### Pre-Release Versions

For pre-releases, use the following format:

```
MAJOR.MINOR.PATCH-PRERELEASE.IDENTIFIER
```

- `1.0.0-alpha.1`: Alpha release
- `1.0.0-beta.1`: Beta release
- `1.0.0-rc.1`: Release candidate

## Release Types

### Patch Release

**When to use**:
- Bug fixes
- Security patches
- Documentation updates
- Performance improvements (non-breaking)

**Impact**: Low risk, no breaking changes

**Frequency**: As needed

### Minor Release

**When to use**:
- New features
- New tools
- Enhancements to existing functionality
- Deprecations (with migration path)

**Impact**: Medium risk, backwards-compatible

**Frequency**: Monthly or quarterly

### Major Release

**When to use**:
- Breaking changes
- Removal of deprecated features
- Major architectural changes
- Technology stack upgrades

**Impact**: High risk, requires migration

**Frequency**: Annually or as needed

## Release Process

### 1. Planning

- Create release issue/issue tracker
- Define release scope and features
- Estimate timeline and resources
- Assign release manager

### 2. Development

- Create release branch from `develop`
- Branch name: `release/vX.Y.Z`
- Implement features and fixes
- Update documentation

### 3. Testing

- Run full test suite
- Perform integration testing
- Conduct security audit
- Performance testing
- User acceptance testing (for major releases)

### 4. Pre-Release

- Update version numbers
- Update CHANGELOG
- Create release notes
- Tag release candidate
- Deploy to staging environment

### 5. Release

- Merge release branch to `main`
- Create Git tag
- Deploy to production
- Publish release notes
- Announce release

### 6. Post-Release

- Monitor production metrics
- Address any issues
- Update documentation
- Archive release branch
- Plan next release

## Pre-Release Checklist

### Code Quality

- [ ] All tests passing (pytest)
- [ ] Code coverage ≥ 80%
- [ ] No linting errors (flake8)
- [ ] No type checking errors (mypy)
- [ ] Code formatted with Black
- [ ] No security vulnerabilities (bandit)

### Documentation

- [ ] API documentation updated (API_REFERENCE.md)
- [ ] Tool guide updated (TOOL_GUIDE.md)
- [ ] Architecture documentation updated (ARCHITECTURE.md)
- [ ] CHANGELOG.md updated
- [ ] README.md updated (if needed)
- [ ] Migration guide created (for major releases)

### Testing

- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Manual testing completed
- [ ] Performance benchmarks run
- [ ] Security audit completed

### Deployment

- [ ] Database migrations tested
- [ ] Configuration files updated
- [ ] Environment variables documented
- [ ] Deployment scripts tested
- [ ] Rollback procedure verified
- [ ] Monitoring dashboards updated

### Communication

- [ ] Release notes prepared
- [ ] Stakeholders notified
- [ ] Support team briefed
- [ ] User documentation updated
- [ ] Release announcement drafted

## Release Steps

### Step 1: Create Release Branch

```bash
# Ensure develop branch is up to date
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/v1.0.0

# Update version in pyproject.toml
# Update version in __init__.py
```

### Step 2: Update Version Numbers

**pyproject.toml**:
```toml
[project]
name = "wms-mcp-server"
version = "1.0.0"
```

**app/__init__.py**:
```python
__version__ = "1.0.0"
```

### Step 3: Update CHANGELOG

```markdown
# Changelog

## [1.0.0] - 2024-06-15

### Added
- Initial release with 19 WMS tools
- Inventory & Slotting tools
- Transactions & Movements tools
- Concurrency & Monitoring tools
- Alerts & Reports tools
- Advanced subsystem tools

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A
```

### Step 4: Run Full Test Suite

```bash
# Run all tests
pytest --cov=app --cov-report=html

# Run linting
flake8 app/ tests/
mypy app/

# Run security check
bandit -r app/
```

### Step 5: Create Release Candidate

```bash
# Commit changes
git add .
git commit -m "chore: prepare release v1.0.0"

# Push to remote
git push origin release/v1.0.0

# Create tag
git tag -a v1.0.0-rc.1 -m "Release candidate v1.0.0-rc.1"
git push origin v1.0.0-rc.1
```

### Step 6: Deploy to Staging

```bash
# Build Docker image
docker build -t wms-mcp-server:1.0.0-rc.1 .

# Tag for staging
docker tag wms-mcp-server:1.0.0-rc.1 registry.example.com/wms-mcp-server:staging

# Push to registry
docker push registry.example.com/wms-mcp-server:staging

# Deploy to staging environment
# (Use your deployment tool: kubectl, helm, etc.)
```

### Step 7: Staging Verification

- Run smoke tests on staging
- Verify all tools working
- Check database migrations
- Monitor error rates
- Verify performance metrics

### Step 8: Merge to Main

```bash
# If staging verification passes
git checkout main
git merge release/v1.0.0

# Push to main
git push origin main
```

### Step 9: Create Release Tag

```bash
# Create final release tag
git tag -a v1.0.0 -m "Release v1.0.0"

# Push tag
git push origin v1.0.0
```

### Step 10: Deploy to Production

```bash
# Build production image
docker build -t wms-mcp-server:1.0.0 .

# Tag for production
docker tag wms-mcp-server:1.0.0 registry.example.com/wms-mcp-server:1.0.0
docker tag wms-mcp-server:1.0.0 registry.example.com/wms-mcp-server:latest

# Push to registry
docker push registry.example.com/wms-mcp-server:1.0.0
docker push registry.example.com/wms-mcp-server:latest

# Deploy to production
# (Use your deployment tool: kubectl, helm, etc.)
```

### Step 11: Backmerge to Develop

```bash
# Merge main back to develop
git checkout develop
git merge main

# Push to develop
git push origin develop
```

### Step 12: Create GitHub Release

```bash
# Use GitHub CLI or web interface
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes "Release notes here" \
  --draft
```

### Step 13: Publish Release

- Review release notes
- Publish GitHub release
- Announce to stakeholders
- Update documentation portal

## Post-Release Steps

### Monitoring

- Monitor application metrics for 24-48 hours
- Check error rates and logs
- Verify performance benchmarks
- Monitor database performance
- Check queue backlogs

### Documentation

- Update deployment documentation
- Update version in README
- Archive release notes
- Update migration guides
- Update API documentation

### Communication

- Send release announcement email
- Update status page
- Post release notes to community
- Brief support team
- Update project roadmap

### Cleanup

- Delete release branch
- Archive release artifacts
- Clean up staging environment
- Update issue tracker
- Close related issues

## Rollback Procedure

### When to Rollback

- Critical bugs discovered
- Security vulnerabilities found
- Performance degradation
- Data corruption issues
- Integration failures

### Rollback Steps

#### Immediate Rollback

```bash
# Identify previous stable version
git tag -l "v*" | sort -V | tail -n 2

# Checkout previous version
git checkout v0.9.0

# Build and deploy previous version
docker build -t wms-mcp-server:0.9.0 .
docker tag wms-mcp-server:0.9.0 registry.example.com/wms-mcp-server:latest
docker push registry.example.com/wms-mcp-server:latest

# Deploy to production
# (Use your deployment tool)
```

#### Database Rollback

```bash
# Rollback database migrations
python -m alembic downgrade -1

# Or rollback to specific version
python -m alembic downgrade <target_version>
```

#### Configuration Rollback

```bash
# Restore previous configuration
# (Use your configuration management tool)
```

### Rollback Verification

- Verify application is running
- Run smoke tests
- Check error rates
- Verify data integrity
- Monitor performance

### Post-Rollback

- Document rollback reason
- Create incident report
- Schedule fix for next release
- Update stakeholders
- Review release process

## Release Notes

### Release Notes Template

```markdown
# Release v1.0.0

## Overview
Brief description of the release

## Highlights
Key features and improvements

## New Features
- Feature 1 description
- Feature 2 description

## Enhancements
- Enhancement 1 description
- Enhancement 2 description

## Bug Fixes
- Bug fix 1 description
- Bug fix 2 description

## Breaking Changes
- Breaking change 1 description
- Migration instructions

## Deprecations
- Deprecated feature 1 description
- Removal timeline

## Security
- Security fix 1 description
- Security advisory link

## Known Issues
- Known issue 1 description
- Workaround

## Upgrade Instructions
Step-by-step upgrade guide

## Migration Guide
Detailed migration instructions (for major releases)

## Contributors
List of contributors

## Support
Support information and links
```

### Release Notes Example

```markdown
# Release v1.0.0

## Overview
Initial stable release of WMS MCP Server with 19 warehouse management tools.

## Highlights
- Complete tool set for warehouse operations
- Distributed locking for concurrent operations
- Comprehensive error handling
- Full API documentation

## New Features
- Inventory & Slotting tools (4 tools)
- Transactions & Movements tools (3 tools)
- Concurrency & Monitoring tools (3 tools)
- Alerts & Reports tools (2 tools)
- Advanced subsystem tools (7 tools)

## Enhancements
- Async/await for all I/O operations
- Pydantic validation for all inputs
- Comprehensive error codes
- Rate limiting per tool category

## Bug Fixes
- N/A (initial release)

## Breaking Changes
- N/A (initial release)

## Deprecations
- N/A (initial release)

## Security
- API key-based authentication
- Role-based access control
- Input validation on all tools

## Known Issues
- No known issues

## Upgrade Instructions
This is the initial release. No upgrade needed.

## Migration Guide
N/A (initial release)

## Contributors
- John Doe (Lead Developer)
- Jane Smith (Documentation)
- Bob Johnson (Testing)

## Support
For support, please open an issue on GitHub or contact support@example.com
```

## Release Schedule

### Regular Releases

- **Patch releases**: As needed (bug fixes)
- **Minor releases**: Monthly (new features)
- **Major releases**: Annually (breaking changes)

### Release Calendar

| Quarter | Release Type | Target Date |
|---------|-------------|-------------|
| Q1 2024 | Minor (v1.1.0) | March 2024 |
| Q2 2024 | Minor (v1.2.0) | June 2024 |
| Q3 2024 | Major (v2.0.0) | September 2024 |
| Q4 2024 | Minor (v2.1.0) | December 2024 |

### Emergency Releases

Emergency releases can be made at any time for:
- Critical security vulnerabilities
- Data loss bugs
- Production outages

## Release Roles

### Release Manager

**Responsibilities**:
- Coordinate release process
- Ensure all checklist items completed
- Make final go/no-go decision
- Handle release communication

### Developer

**Responsibilities**:
- Implement features and fixes
- Write tests
- Update documentation
- Fix release-blocking issues

### QA Engineer

**Responsibilities**:
- Test release candidate
- Verify bug fixes
- Perform regression testing
- Sign off on release

### DevOps Engineer

**Responsibilities**:
- Build deployment artifacts
- Deploy to staging
- Deploy to production
- Monitor deployment

### Documentation Writer

**Responsibilities**:
- Update release notes
- Update user documentation
- Create migration guides
- Update API documentation

## Release Metrics

Track the following metrics for each release:

- Release duration (planning to deployment)
- Number of bugs fixed
- Number of features added
- Test coverage percentage
- Deployment success rate
- Post-release bug count
- Time to rollback (if needed)

## Continuous Improvement

After each release, conduct a retrospective to:

- Identify what went well
- Identify areas for improvement
- Update release process
- Update documentation
- Share lessons learned

## Resources

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
