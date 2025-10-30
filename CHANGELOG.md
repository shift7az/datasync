# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release
- GitHub Actions workflow for validation
- Issue templates for bug reports and feature requests
- Contribution guidelines
- Code of Conduct

## [1.0.0] - 2025-10-30

### Added
- Cross-account S3 migration setup using AWS DataSync
- Automatic bucket policy backups with one-click restore
- Safe policy merging (preserves existing statements)
- IAM role creation with confused deputy protection
- Bucket access verification
- Retry logic with exponential backoff
- Automatic rollback on task creation failures
- Dry-run mode for safe preview
- Colored logging with custom SUCCESS level
- Multi-migration support in single run
- Comprehensive README documentation
- Example YAML configuration file

### Security
- Confused deputy protection in IAM trust policy
- Cross-account conditions on destination permissions
- Least privilege S3 permissions
- No credentials in code (uses AWS CLI profiles)

### Safety Features
- Never modifies existing IAM roles (reuse-only)
- Never replaces bucket policies (merge-only)
- Automatic backups before any changes
- No auto-start of data transfers (manual approval required)
- Early failure detection with bucket verification
- Automatic resource cleanup on failures

[Unreleased]: https://github.com/shift7az/datasync/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shift7az/datasync/releases/tag/v1.0.0
