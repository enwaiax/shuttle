# {{RIPER-5:
#   Action: "Added"
#   Task_ID: "7037bed8-d479-44e6-9198-c81f69b9d05d"
#   Timestamp: "2025-08-05T20:50:09+08:00"
#   Authoring_Role: "LD"
#   Principle_Applied: "文档即代码 + 用户友好性"
#   Quality_Check: "完整的测试文档，包含运行指导、覆盖率要求、测试架构"
# }}
# {{START_MODIFICATIONS}}
# FastMCP SSH Server - Test Suite Documentation

## 📋 Overview

This directory contains the comprehensive test suite for the FastMCP SSH Server Python implementation. The test suite ensures functionality, reliability, and compatibility with the TypeScript version.

## 🏗️ Test Architecture

### Test Organization

```
tests/
├── test_ssh_manager.py      # SSH connection manager tests
├── test_mcp_tools.py        # MCP tool implementation tests
├── test_cli.py              # CLI argument parsing tests
├── test_integration.py      # End-to-end integration tests
├── test_mcp_integration.py  # FastMCP server integration tests (in-memory)
├── run_tests.py            # Test runner script
├── conftest.py             # pytest configuration and fixtures
├── __init__.py             # Test package initialization
└── README.md               # This documentation
```

### Test Categories

- **Unit Tests** (`@pytest.mark.unit`): Test individual components in isolation
- **Integration Tests** (`@pytest.mark.integration`): Test component interactions
- **SSH Tests** (`@pytest.mark.ssh`): Tests requiring SSH connection mocking
- **MCP Tests** (`@pytest.mark.mcp`): MCP tool functionality tests
- **CLI Tests** (`@pytest.mark.cli`): Command line interface tests
- **Security Tests** (`@pytest.mark.security`): Security validation tests
- **Performance Tests** (`@pytest.mark.performance`): Performance and load tests

## 🚀 Running Tests

### Prerequisites

Ensure you have the required testing dependencies:

```bash
# From repo root (uses pyproject dev group)
uv sync --group dev
```

### Quick Start

```bash
# Run all tests with coverage
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --unit          # Unit tests only
python tests/run_tests.py --integration   # Integration tests only
python tests/run_tests.py --fast          # Fast tests only (excludes slow tests)
python tests/run_tests.py --security      # Security tests only

# Run with detailed output
python tests/run_tests.py --verbose

# Generate coverage report
python tests/run_tests.py --coverage
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ssh_manager.py

# Run with coverage
pytest --cov=src/python_ssh_mcp --cov-report=html

# Run specific test class
pytest tests/test_ssh_manager.py::TestSSHConnectionManager

# Run specific test method
pytest tests/test_ssh_manager.py::TestSSHConnectionManager::test_singleton_pattern

# Run tests matching pattern
pytest -k "test_connection"

# Run tests with specific markers
pytest -m "unit and not slow"
```

## 📊 Coverage Requirements

The test suite maintains high code coverage standards:

- **Target Coverage**: 90%+ overall
- **Minimum Coverage**: 85% per module
- **Critical Components**: 95%+ coverage for SSH manager and MCP tools

### Coverage Reports

```bash
# Generate HTML coverage report
python tests/run_tests.py --coverage

# View coverage in browser
open htmlcov/index.html

# Generate terminal coverage report
pytest --cov=src/python_ssh_mcp --cov-report=term-missing
```

## 🧪 Test Descriptions

### SSH Manager Tests (`test_ssh_manager.py`)

Tests for the core SSH connection management functionality:

- **Connection Management**: Connection establishment, pooling, and cleanup
- **Authentication**: Password and private key authentication methods
- **Security Validation**: Command whitelist/blacklist enforcement
- **Error Handling**: Connection failures, authentication errors, timeouts
- **Concurrent Operations**: Multiple simultaneous connections and commands
- **Resource Management**: Memory usage and connection cleanup

**Key Test Classes:**
- `TestSSHConnectionManager`: Core connection manager functionality
- `TestSecurityValidator`: Security validation mechanisms

### MCP Tools Tests (`test_mcp_tools.py`)

Tests for FastMCP tool implementations:

- **Tool Registration**: Proper registration with FastMCP framework
- **execute-command Tool**: Command execution with security validation
- **upload Tool**: File upload functionality and error handling
- **download Tool**: File download functionality and error handling
- **list-servers Tool**: Server information listing
- **Error Handling**: Consistent error response formatting
- **Integration**: Tool interaction with SSH manager

**Key Test Classes:**
- `TestMCPToolRegistration`: Tool registration verification
- `TestExecuteCommandTool`: Command execution tool tests
- `TestUploadTool`: File upload tool tests
- `TestDownloadTool`: File download tool tests
- `TestListServersTool`: Server listing tool tests
- `TestMCPToolIntegration`: Cross-component integration

### CLI Tests (`test_cli.py`)

Tests for command line interface and argument parsing:

- **Single Connection Mode**: Parsing individual SSH connection parameters
- **Multiple Connection Mode**: Parsing multiple SSH connection strings
- **SSH String Parsing**: Various SSH connection string formats
- **Security Configuration**: Allow/deny command list parsing
- **Authentication Methods**: Password vs. private key configuration
- **Error Validation**: Invalid parameter handling and error messages
- **Typer Integration**: CLI framework integration and validation

**Key Test Classes:**
- `TestSSHConnectionStringParsing`: SSH connection string parsing
- `TestCLIArgumentParsing`: Complete CLI argument processing
- `TestCLIErrorHandling`: Error handling and validation
- `TestCLIConfigGeneration`: SSH config object generation
- `TestTyperIntegration`: Typer framework integration

### Integration Tests (`test_integration.py`)

End-to-end tests for complete system functionality:

- **Full Server Integration**: Complete server startup and initialization
- **CLI to MCP Pipeline**: Full command line to MCP tool execution flow
- **Multi-Server Operations**: Operations across multiple SSH connections
- **Error Propagation**: Error handling across all system layers
- **Performance Testing**: Concurrent operations and resource usage
- **Recovery Testing**: Error recovery and system resilience

**Key Test Classes:**
- `TestFullServerIntegration`: Complete server functionality
- `TestMCPToolsIntegration`: End-to-end tool operation
- `TestLoggingIntegration`: Logging system integration
- `TestPerformanceIntegration`: Performance and scalability
- `TestErrorRecoveryIntegration`: Error recovery and resilience

## 🔧 Test Configuration

### pytest Configuration (`pytest.ini`)

The test suite uses pytest with the following key configurations:

- **Async Support**: Automatic asyncio test detection and execution
- **Coverage**: 90% minimum coverage requirement
- **Markers**: Test categorization for selective execution
- **Timeouts**: 300-second maximum test execution time
- **Reporting**: Multiple coverage report formats (terminal, HTML, XML)

### Test Fixtures (`conftest.py`)

Common test fixtures and utilities:

- **Event Loop**: Shared asyncio event loop for async tests
- **Mock SSH Config**: Standard SSH configuration for testing
- **Mock FastMCP Server**: FastMCP server mock for tool testing

## 🐛 Debugging Tests

### Running Specific Tests

```bash
# Run single test with detailed output
pytest tests/test_ssh_manager.py::TestSSHConnectionManager::test_singleton_pattern -v -s

# Run tests with pdb debugger
pytest --pdb tests/test_ssh_manager.py

# Run tests with detailed traceback
pytest --tb=long tests/test_ssh_manager.py
```

### Common Issues

1. **Async Test Failures**
   - Ensure `pytest-asyncio` is installed
   - Check that async tests are properly marked with `async def`

2. **Mock-Related Issues**
   - Verify mock patches are correctly scoped
   - Check that mock return values match expected types

3. **Import Errors**
   - Ensure `src` is in Python path
   - Check that all required dependencies are installed

## 📈 Performance Benchmarks

The test suite includes performance benchmarks for critical operations:

- **Connection Establishment**: < 100ms per connection
- **Command Execution**: < 50ms overhead per command
- **File Transfer**: > 10MB/s for large files
- **Concurrent Operations**: Support for 10+ simultaneous operations

## 🔒 Security Test Coverage

Security tests ensure robust protection:

- **Command Injection**: Prevention of malicious command execution
- **Path Traversal**: File operation path validation
- **Authentication**: Secure credential handling
- **Authorization**: Proper command filtering enforcement

## 🏃‍♂️ Continuous Integration

For CI/CD pipelines:

```bash
# Fast test suite for rapid feedback
python tests/run_tests.py --fast --no-coverage

# Complete test suite with coverage
python tests/run_tests.py --coverage

# Security-focused testing
python tests/run_tests.py --security --lint
```

## 📝 Adding New Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<functionality_description>`

### Test Structure Template

```python
class TestNewComponent:
    """Test suite for new component functionality."""

    @pytest.fixture
    def component_fixture(self):
        """Provide test component instance."""
        return NewComponent()

    async def test_basic_functionality(self, component_fixture):
        """Test basic component functionality."""
        # Arrange
        input_data = "test input"

        # Act
        result = await component_fixture.process(input_data)

        # Assert
        assert result == "expected output"

    async def test_error_handling(self, component_fixture):
        """Test component error handling."""
        with pytest.raises(ExpectedError, match="error message"):
            await component_fixture.process(invalid_input)
```

### Mocking Guidelines

- Use `unittest.mock.AsyncMock` for async methods
- Use `unittest.mock.MagicMock` for sync methods
- Patch at the appropriate level (usually the module being tested)
- Verify mock calls with `assert_called_with()`

## 🎯 Test Quality Guidelines

1. **Independence**: Tests should not depend on each other
2. **Repeatability**: Tests should produce consistent results
3. **Fast Execution**: Unit tests should complete in < 1 second
4. **Clear Assertions**: Each test should have clear pass/fail criteria
5. **Comprehensive Coverage**: Test both success and failure scenarios
6. **Realistic Mocking**: Mocks should behave like real components

## 🔍 Code Quality Checks

In addition to tests, the suite includes code quality verification:

```bash
# Run linting
python tests/run_tests.py --lint

# Or run individually
ruff check src/
mypy src/
black --check src/
isort --check-only src/
```

## 📞 Support

For test-related issues:

1. Check this documentation for common solutions
2. Review test output for specific error details
3. Run tests with `--verbose` for detailed information
4. Use `--pdb` flag to debug failing tests interactively

The test suite is designed to be comprehensive, maintainable, and provide confidence in the FastMCP SSH server implementation.
# {{END_MODIFICATIONS}}
