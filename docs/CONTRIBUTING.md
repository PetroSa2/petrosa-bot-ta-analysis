# Contributing Guidelines

Welcome to the Petrosa TA Bot project! This guide will help you contribute effectively.

## 🤝 How to Contribute

### Types of Contributions

- **Bug Reports**: Report bugs and issues
- **Feature Requests**: Suggest new features
- **Code Contributions**: Submit code improvements
- **Documentation**: Improve documentation
- **Testing**: Add or improve tests
- **Performance**: Optimize performance

## 🚀 Getting Started

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/your-username/ta-bot.git
cd ta-bot

# Add upstream remote
git remote add upstream https://github.com/petrosa/ta-bot.git
```

### 2. Setup Development Environment

```bash
# Setup development environment
make setup

# Install development dependencies
make install-dev

# Run tests to ensure everything works
make test
```

### 3. Create a Feature Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/your-bug-description
```

## 📝 Development Workflow

### 1. Make Your Changes

Follow the coding standards:

```python
# Use type hints
def calculate_indicator(data: pd.DataFrame) -> float:
    """Calculate technical indicator.
    
    Args:
        data: OHLCV data
        
    Returns:
        Calculated indicator value
    """
    pass
```

### 2. Write Tests

```python
# tests/test_your_feature.py
import pytest
from ta_bot.your_module import YourFunction

class TestYourFeature:
    """Test cases for your feature."""
    
    def test_your_function(self):
        """Test your function."""
        result = YourFunction()
        assert result is not None
```

### 3. Run Quality Checks

```bash
# Run all quality checks
make lint
make test
make security

# Or run complete pipeline
make pipeline
```

### 4. Commit Your Changes

```bash
# Add your changes
git add .

# Commit with descriptive message
git commit -m "feat: add new technical indicator

- Add RSI divergence detection
- Include unit tests with 95% coverage
- Update documentation

Closes #123"
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] **Tests Pass**: All tests pass locally
- [ ] **Code Quality**: Linting and formatting pass
- [ ] **Coverage**: New code has adequate test coverage
- [ ] **Documentation**: Code is properly documented
- [ ] **Security**: No security vulnerabilities introduced

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes introduced

## Related Issues
Closes #123
```

## 🎯 Contribution Areas

### Core Engine

- **Signal Engine**: Improve signal generation logic
- **Indicators**: Add new technical indicators
- **Strategies**: Implement new trading strategies
- **Confidence**: Improve confidence calculation

### Services

- **NATS Integration**: Enhance message handling
- **API Integration**: Improve signal publishing
- **Health Checks**: Add new health endpoints

### Infrastructure

- **Docker**: Optimize container configuration
- **Kubernetes**: Improve deployment manifests
- **CI/CD**: Enhance automation pipeline

### Documentation

- **API Docs**: Improve API documentation
- **User Guides**: Create user tutorials
- **Architecture**: Document system design

## 📊 Code Quality Standards

### Python Style Guide

Follow **PEP 8** and use **Black** for formatting:

```python
# Good
def calculate_rsi(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate RSI indicator."""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]
```

### Type Hints

Always use type hints:

```python
from typing import Dict, List, Optional, Any
import pandas as pd

def analyze_market_data(
    candle_data: pd.DataFrame,
    indicators: Dict[str, float]
) -> Optional[Signal]:
    """Analyze market data and return signal."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_macd(data: pd.DataFrame) -> Dict[str, float]:
    """Calculate MACD indicator.
    
    Args:
        data: DataFrame with OHLCV data
        
    Returns:
        Dictionary containing MACD, signal, and histogram values
        
    Raises:
        ValueError: If data is empty or missing required columns
    """
    pass
```

## 🧪 Testing Requirements

### Test Coverage

- **Minimum Coverage**: 90% for new code
- **Critical Paths**: 100% coverage for core logic
- **Edge Cases**: Test boundary conditions
- **Error Handling**: Test exception scenarios

### Test Structure

```python
# tests/test_your_module.py
import pytest
from ta_bot.your_module import YourClass

class TestYourClass:
    """Test cases for YourClass."""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return YourClass()
    
    def test_normal_operation(self, instance):
        """Test normal operation."""
        result = instance.method()
        assert result is not None
    
    def test_edge_case(self, instance):
        """Test edge case."""
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

## 🔒 Security Guidelines

### Code Security

- **No Hardcoded Secrets**: Use environment variables
- **Input Validation**: Validate all inputs
- **Error Handling**: Don't expose sensitive information
- **Dependencies**: Keep dependencies updated

### Security Checklist

- [ ] No hardcoded API keys or secrets
- [ ] Input validation implemented
- [ ] Error messages don't expose internals
- [ ] Dependencies scanned for vulnerabilities
- [ ] Security tests included

## 📚 Documentation Standards

### Code Documentation

```python
class SignalEngine:
    """Core signal generation engine.
    
    The SignalEngine coordinates all trading strategies and generates
    trading signals based on technical analysis.
    
    Attributes:
        strategies: List of trading strategies
        indicators: Technical indicators calculator
        confidence: Confidence calculation engine
    """
    
    def process_candle(self, data: pd.DataFrame) -> List[Signal]:
        """Process candle data through all strategies.
        
        Args:
            data: OHLCV candle data
            
        Returns:
            List of generated signals
            
        Raises:
            ValueError: If data is invalid or empty
        """
        pass
```

### README Updates

When adding new features, update:

- **README.md**: Add feature description
- **API Documentation**: Document new endpoints
- **Configuration**: Document new settings
- **Examples**: Provide usage examples

## 🚨 Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: Ubuntu 20.04
- Python: 3.11.0
- Version: v1.0.0

## Additional Information
Screenshots, logs, etc.
```

### Feature Requests

Use the feature request template:

```markdown
## Feature Description
Clear description of the feature

## Use Case
Why this feature is needed

## Proposed Solution
How you think it should work

## Alternatives Considered
Other approaches you considered

## Additional Information
Mockups, examples, etc.
```

## 🤝 Code Review Process

### Review Guidelines

- **Be Respectful**: Constructive feedback only
- **Be Thorough**: Check code quality, tests, docs
- **Be Prompt**: Respond within 24 hours
- **Be Helpful**: Suggest improvements

### Review Checklist

- [ ] **Code Quality**: Follows style guidelines
- [ ] **Functionality**: Works as intended
- [ ] **Tests**: Adequate test coverage
- [ ] **Documentation**: Code is documented
- [ ] **Security**: No security issues
- [ ] **Performance**: No performance regressions

### Review Comments

```markdown
# Good review comment
This looks good overall! A few suggestions:

1. Consider adding error handling for edge case X
2. The function name could be more descriptive
3. Add a test for the new edge case

Great work on the implementation!
```

## 📊 Performance Guidelines

### Performance Requirements

- **Response Time**: API endpoints < 100ms
- **Memory Usage**: Reasonable memory footprint
- **CPU Usage**: Efficient algorithm usage
- **Scalability**: Handle increased load

### Performance Testing

```python
def test_performance():
    """Test performance requirements."""
    start_time = time.time()
    
    # Run operation
    result = function_to_test()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Assert performance requirements
    assert duration < 0.1  # 100ms
    assert memory_usage < 100 * 1024 * 1024  # 100MB
```

## 🎉 Recognition

### Contributor Recognition

- **Contributors List**: Added to README.md
- **Release Notes**: Mentioned in release notes
- **Contributor Badge**: GitHub contributor badge
- **Special Thanks**: Acknowledged in documentation

### Contribution Levels

- **Bronze**: 1-5 contributions
- **Silver**: 6-15 contributions
- **Gold**: 16+ contributions
- **Platinum**: Major contributions

## 📞 Getting Help

### Communication Channels

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Pull Requests**: For code reviews
- **Email**: For security issues

### Getting Started Help

```bash
# Need help getting started?
# 1. Check the documentation
# 2. Look at existing issues
# 3. Join discussions
# 4. Ask questions in issues
```

## 📋 Contribution Checklist

### Before Contributing

- [ ] **Read Documentation**: Understand the project
- [ ] **Check Issues**: Look for existing issues
- [ ] **Join Community**: Participate in discussions
- [ ] **Setup Environment**: Get development environment ready

### During Development

- [ ] **Follow Standards**: Use project coding standards
- [ ] **Write Tests**: Include comprehensive tests
- [ ] **Update Docs**: Keep documentation current
- [ ] **Test Thoroughly**: Ensure everything works

### Before Submitting

- [ ] **Self Review**: Review your own code
- [ ] **Quality Checks**: Run all quality checks
- [ ] **Test Coverage**: Ensure adequate coverage
- [ ] **Documentation**: Update relevant docs

## 🔗 Related Documentation

- **Development Guide**: See [Development Guide](./DEVELOPMENT.md) for development workflow
- **Testing Guide**: Check [Testing Guide](./TESTING.md) for testing guidelines
- **API Reference**: Review [API Reference](./API_REFERENCE.md) for API development
- **Configuration**: Read [Configuration](./CONFIGURATION.md) for environment setup

---

**Thank you for contributing to Petrosa TA Bot!** 🚀

Your contributions help make this project better for everyone in the trading community. 