# Contributing to Labyrinth

Thank you for your interest in contributing to Labyrinth! This document provides guidelines and instructions for contributing to the project.

## 🚀 Quick Start

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/dariopalladino/labyrinth.git
   cd labyrinth
   ```

2. **Set up development environment**
   ```bash
   make setup-dev
   # or manually:
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Run tests to ensure everything works**
   ```bash
   make test
   ```

## 🔧 Development Workflow

### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run formatting and linting:
```bash
make format  # Format code
make lint    # Check code quality
```

### Testing

We use pytest for testing. Please ensure all tests pass and write tests for new functionality.

```bash
make test         # Run all tests
make test-cov     # Run tests with coverage report
```

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation as needed
   - Follow existing code patterns

3. **Test your changes**
   ```bash
   make check  # Run all checks (lint + test)
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Use [conventional commits](https://www.conventionalcommits.org/) format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `test:` for test changes
   - `refactor:` for code refactoring

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 What to Contribute

### 🐛 Bug Reports

Before creating bug reports, please check existing issues. When creating a bug report, include:

- Clear title and description
- Steps to reproduce
- Expected vs actual behavior  
- Environment details (Python version, OS, etc.)
- Code samples or error messages

### 💡 Feature Requests

For feature requests, please:

- Check if the feature already exists or is planned
- Provide clear use cases and rationale
- Consider implementation complexity
- Be open to discussion and feedback

### 🔨 Code Contributions

Great areas to contribute:

1. **Core Features**
   - Enhanced A2A SDK integration
   - New message types and formats
   - Task management improvements
   - Error handling enhancements

2. **Documentation**
   - Code examples
   - Tutorials and guides
   - API documentation
   - README improvements

3. **Testing**
   - Unit tests
   - Integration tests
   - Performance tests
   - Test utilities

4. **Utilities**
   - Configuration management
   - Logging improvements  
   - Development tools
   - CI/CD enhancements

## 🏗️ Project Structure

```
labyrinth/
├── labyrinth/           # Main package
│   ├── client/          # Client-side components
│   ├── server/          # Server-side components  
│   ├── types/           # Type definitions
│   └── utils/           # Utilities
├── tests/               # Test suite
├── examples/            # Usage examples
├── docs/                # Documentation
└── .github/             # CI/CD workflows
```

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)  
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated for significant changes

### Pull Request Template

When creating a PR, please include:

- **Description**: What does this PR do?
- **Motivation**: Why is this change needed?
- **Testing**: How was this tested?
- **Breaking Changes**: Any breaking changes?
- **Checklist**: Mark completed items

### Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. Address any feedback
4. Squash commits if requested
5. Merge once approved

## 🤝 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors:**
- Harassment, discriminatory language, or unwelcome attention
- Trolling, insulting/derogatory comments, personal or political attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct reasonably considered inappropriate

### Enforcement

Report unacceptable behavior to [aionsteroid@palladinomail.com](mailto:aionsteroid@palladinomail.com). All reports will be reviewed and investigated promptly and fairly.

## 🆘 Getting Help

- **Documentation**: Check the docs first
- **GitHub Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact aionsteroid@palladinomail.com

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Project documentation

Thank you for contributing to Labyrinth! 🎯
