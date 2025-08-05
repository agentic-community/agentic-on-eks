# Input Validation Implementation

This document describes the input validation system implemented for [Issue #12](https://github.com/agentic-community/agentic-on-eks/issues/12) - "Add input validation".

## Overview

The input validation system provides comprehensive security measures to validate and sanitize user inputs in the UI application. It implements multiple layers of protection against common attack vectors while maintaining usability for legitimate queries.

## Features Implemented

### 🔒 Security Protections

1. **SQL Injection Prevention**
   - Detects SQL keywords (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, etc.)
   - Blocks common SQL injection patterns
   - Validates query structure

2. **XSS Attack Prevention**
   - Detects `<script>` tags and JavaScript code
   - Blocks HTML injection attempts
   - Sanitizes input using HTML escaping

3. **Command Injection Detection**
   - Blocks system commands (`rm`, `ls`, `cat`, etc.)
   - Prevents execution of dangerous commands
   - Validates against shell injection patterns

4. **Path Traversal Protection**
   - Blocks `../` and `..\` patterns
   - Prevents directory traversal attacks
   - Validates file path references

5. **Input Length Validation**
   - Enforces maximum query length (500 characters)
   - Prevents DoS attacks through oversized inputs
   - Validates minimum input length (3 characters)

### 🎯 Domain-Specific Validation

1. **HR Domain Keywords**
   - `employee`, `name`, `vacation`, `holiday`, `leave`, `days`
   - `public`, `holidays`, `schedule`, `attendance`, `profile`
   - `contact`, `phone`, `email`, `address`, `department`

2. **Finance Domain Keywords**
   - `salary`, `annual`, `monthly`, `pay`, `payment`, `compensation`
   - `bonus`, `raise`, `promotion`, `deduction`, `tax`, `benefits`
   - `retirement`, `401k`, `pension`, `expense`, `budget`

3. **General Query Keywords**
   - Question words: `what`, `how`, `when`, `where`, `who`, `why`
   - Action words: `show`, `tell`, `give`, `find`, `get`, `calculate`

### 🛡️ Employee ID Validation

- **Format**: `EMP####` (e.g., `EMP0001`, `EMP9999`)
- **Case Insensitive**: Automatically converts to uppercase
- **Length Validation**: Exactly 7 characters
- **Pattern Matching**: Strict regex validation

## Security Levels

### 🔓 Low Security
- Basic validation only
- Minimal restrictions
- Suitable for development/testing

### 🔒 Medium Security (Default)
- Comprehensive validation
- Malicious pattern detection
- Domain keyword validation
- Input sanitization

### 🔐 High Security
- All medium security features
- Additional DoS protection
- Repeated character detection
- Enhanced suspicious pattern checking

## Usage

### Basic Validation

```python
from input_validation import validate_user_input, InputType

# Validate a query
result = validate_user_input("What is the name of employee EMP0002?", InputType.QUERY)

if result.is_valid:
    print("Query is valid")
    print(f"Sanitized input: {result.sanitized_input}")
else:
    print("Query is invalid")
    for error in result.errors:
        print(f"Error: {error}")
```

### Employee ID Validation

```python
# Validate employee ID
result = validate_user_input("EMP0001", InputType.EMPLOYEE_ID)

if result.is_valid:
    print("Employee ID is valid")
else:
    print("Employee ID is invalid")
```

### Custom Validation Level

```python
from input_validation import get_validator, ValidationLevel

# Create validator with high security
validator = get_validator(ValidationLevel.HIGH)
result = validator.validate_query("Your query here")
```

## Integration with UI

The validation system is integrated into the main UI application:

1. **Pre-processing**: All user inputs are validated before processing
2. **Error Display**: Validation errors are shown to users with clear explanations
3. **Warning System**: Non-critical issues are shown as warnings
4. **Sanitization**: All inputs are sanitized before being sent to agents
5. **Security Dashboard**: Validation statistics are displayed in the sidebar

## Test Cases

Run the test suite to see validation in action:

```bash
cd ui
python test_validation.py
```

### Test Scenarios

1. **Valid Queries**
   - "What is the name of employee EMP0002?"
   - "What is the annual salary of EMP0003?"
   - "How many vacation days does EMP0001 have left?"

2. **Malicious Inputs** (Blocked)
   - `<script>alert('xss')</script>` - XSS attack
   - `SELECT * FROM employees` - SQL injection
   - `../etc/passwd` - Path traversal
   - `rm -rf /` - Command injection

3. **Invalid Formats** (Blocked)
   - "Hi" - Too short
   - "A" * 600 - Too long
   - "ABC123" - Invalid employee ID format

## Configuration

### Environment Variables

```bash
# Validation level (optional, defaults to MEDIUM)
VALIDATION_LEVEL=high

# Maximum query length (optional, defaults to 500)
MAX_QUERY_LENGTH=500

# Maximum input length (optional, defaults to 1000)
MAX_INPUT_LENGTH=1000
```

### Custom Patterns

You can extend the validation patterns by modifying `input_validation.py`:

```python
# Add custom malicious patterns
self.malicious_patterns.append(r'your_custom_pattern')

# Add custom allowed keywords
self.allowed_keywords['custom_domain'] = ['keyword1', 'keyword2']
```

## Monitoring and Statistics

The validation system provides statistics for monitoring:

```python
validator = get_validator()
stats = validator.get_validation_stats()

print(f"Security Level: {stats['validation_level']}")
print(f"Max Query Length: {stats['max_query_length']}")
print(f"Malicious Patterns: {stats['malicious_patterns_count']}")
print(f"Allowed Keywords: {stats['allowed_keywords_count']}")
```

## Security Considerations

1. **Defense in Depth**: Multiple validation layers
2. **Fail Secure**: Invalid inputs are rejected
3. **Input Sanitization**: All inputs are sanitized
4. **Logging**: Malicious attempts are logged
5. **Configurable**: Security levels can be adjusted
6. **Domain-Specific**: Tailored for HR/Finance use cases

## Future Enhancements

1. **Machine Learning**: AI-based anomaly detection
2. **Rate Limiting**: Prevent abuse through frequency limits
3. **Behavioral Analysis**: Track user patterns for suspicious activity
4. **Real-time Updates**: Dynamic pattern updates
5. **Integration with SIEM**: Security information and event management

## Contributing

To contribute to the validation system:

1. Add new test cases to `test_validation.py`
2. Extend patterns in `input_validation.py`
3. Update documentation in this README
4. Follow security best practices

## References

- [OWASP Input Validation](https://owasp.org/www-project-proactive-controls/v3/en/c5-validate-inputs)
- [OWASP XSS Prevention](https://owasp.org/www-project-cheat-sheets/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention](https://owasp.org/www-project-cheat-sheets/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) 