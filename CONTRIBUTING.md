# Contributing to RefurbAdmin AI

Thank you for your interest in contributing to RefurbAdmin AI!

This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Respect South African diversity and culture
- Follow POPIA and data protection guidelines

## Getting Started

### Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pricing_tool_est.git
   cd pricing_tool_est
   ```

3. Create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

4. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

5. Run tests:
   ```bash
   pytest
   ```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `test/description` - Tests
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits:
```
feat: add WhatsApp notification support
fix: resolve database connection timeout
docs: update API documentation
test: add unit tests for rate limiter
```

### Pull Request Process

1. Create branch from `main`
2. Make changes
3. Write/update tests
4. Ensure all tests pass
5. Update documentation
6. Submit PR with description
7. Address review feedback
8. Squash commits before merge

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for public APIs

Example:
```python
def calculate_margin(cost: float, price: float) -> float:
    """
    Calculate profit margin percentage.
    
    Args:
        cost: Cost price in ZAR
        price: Selling price in ZAR
        
    Returns:
        Margin percentage (0-100)
    """
    if price <= 0:
        return 0.0
    return ((price - cost) / price) * 100
```

### Testing

- Write unit tests for new features
- Maintain >80% code coverage
- Include integration tests for APIs
- Test with South African data formats

### Security

- Never commit secrets or credentials
- Use environment variables
- Follow OWASP guidelines
- Sanitize all inputs
- Log security events

## Areas for Contribution

### High Priority

- [ ] Additional payment gateway integrations
- [ ] More South African retailer scrapers
- [ ] Mobile app (React Native/Flutter)
- [ ] Advanced analytics features
- [ ] Multi-language support (Zulu, Xhosa, Afrikaans)

### Medium Priority

- [ ] Email template improvements
- [ ] Report customization
- [ ] API client libraries
- [ ] Performance optimizations

### Documentation

- [ ] Video tutorials
- [ ] API examples
- [ ] Troubleshooting guides
- [ ] Translation to SA languages

## Reporting Issues

### Bug Reports

Include:
- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details
- Screenshots if applicable

### Feature Requests

Include:
- Problem statement
- Proposed solution
- Use case
- Priority/urgency

## Review Process

1. **Automated Checks**
   - Tests must pass
   - Code coverage maintained
   - Linting passes

2. **Code Review**
   - At least one approval required
   - Address all comments
   - Update documentation

3. **Merge**
   - Squash commits
   - Update CHANGELOG
   - Tag release if applicable

## Questions?

- GitHub Discussions: https://github.com/refurbadmin/pricing_tool_est/discussions
- Email: contributors@refurbadmin.co.za
- Documentation: https://docs.refurbadmin.co.za

## Recognition

Contributors will be recognized in:
- CHANGELOG.md
- README.md (Contributors section)
- Annual contributor highlights

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

Thank you for contributing to RefurbAdmin AI! 🇿🇦
