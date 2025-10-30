# Contributing to DataSync Setup Tool

Thank you for your interest in contributing to the DataSync Setup Tool! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/datasync.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, AWS region)
- **Relevant logs or error messages**

Use the bug report template when creating issues.

### Suggesting Enhancements

Enhancement suggestions are welcome! When suggesting an enhancement:

- Use a clear and descriptive title
- Provide a detailed description of the proposed feature
- Explain why this enhancement would be useful
- Include examples of how it would work

Use the feature request template when creating enhancement suggestions.

### Pull Requests

1. **Follow the coding standards** described below
2. **Update documentation** for any changed functionality
3. **Add tests** if applicable
4. **Keep commits atomic** - one logical change per commit
5. **Write clear commit messages** following conventional commits format:
   - `feat: Add new feature`
   - `fix: Fix bug in X`
   - `docs: Update documentation`
   - `refactor: Refactor code`
   - `test: Add tests`

## Development Setup

### Prerequisites

- Python 3.8 or higher
- AWS CLI configured with appropriate profiles
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/datasync.git
cd datasync

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if any)
pip install pylint black pytest
```

### Running Tests

```bash
# Run syntax validation
python -m py_compile datasync_setup_optimized.py

# Run linter
pylint datasync_setup_optimized.py

# Format code
black datasync_setup_optimized.py
```

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Documentation

- Update README.md for user-facing changes
- Add inline comments for complex logic
- Update example configuration files as needed

### Safety and Security

- Never commit credentials or sensitive data
- Follow AWS security best practices
- Use least privilege principles for IAM policies
- Validate all user inputs
- Handle errors gracefully

## Submitting Changes

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No sensitive data in commits

### Pull Request Process

1. **Update the CHANGELOG.md** with details of your changes
2. **Ensure your PR description clearly describes the problem and solution**
3. **Reference any related issues** using keywords like "Fixes #123"
4. **Wait for review** - maintainers will review your PR and may request changes
5. **Address feedback** promptly and professionally

### Review Criteria

Pull requests are evaluated on:

- **Code quality** - clean, readable, maintainable
- **Testing** - appropriate test coverage
- **Documentation** - clear and complete
- **Backwards compatibility** - avoid breaking changes when possible
- **Security** - no vulnerabilities introduced

## Questions?

Feel free to open an issue with the question label if you need help or clarification on anything.

Thank you for contributing! 🎉
