"""
Input Validation Module for UI Application
Implements security measures to validate and sanitize user inputs.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import html

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation levels for different security contexts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class InputType(Enum):
    """Types of input that can be validated"""
    QUERY = "query"
    EMPLOYEE_ID = "employee_id"
    NUMERIC = "numeric"
    TEXT = "text"

@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_input: str
    errors: List[str]
    warnings: List[str]
    validation_level: ValidationLevel

class InputValidator:
    """
    Comprehensive input validation for the UI application.
    Implements security measures to prevent malicious inputs.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MEDIUM):
        self.validation_level = validation_level
        self.max_input_length = 1000
        self.max_query_length = 500
        
        # Define allowed patterns
        self.allowed_patterns = {
            InputType.EMPLOYEE_ID: r'^EMP\d{4}$',
            InputType.NUMERIC: r'^\d+(\.\d+)?$',
            InputType.QUERY: r'^[a-zA-Z0-9\s\-\.,?!@#$%&*()_+\-=\[\]{}|;:"\'<>\/\\]+$'
        }
        
        # Define malicious patterns
        self.malicious_patterns = [
            # SQL Injection patterns
            r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+all\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+select\b)',
            
            # XSS patterns
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            
            # Command injection patterns
            r'(\b(cat|ls|pwd|whoami|id|uname|hostname|ps|top|kill|rm|cp|mv|chmod|chown)\b)',
            r'(\b(echo|printf|print|system|exec|eval|subprocess|os\.system)\b)',
            
            # Path traversal patterns
            r'\.\.\/',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            
            # Special characters that might be used for injection
            r'[<>"\']',
            r'[&]',
            r'[;]',
            r'[|]',
            r'[`]',
            r'[$]',
            
            # Suspicious patterns
            r'(\b(admin|root|sudo|su)\b)',
            r'(\b(password|passwd|secret|key|token)\b)',
            r'(\b(delete|remove|kill|destroy|wipe)\b)',
        ]
        
        # Define allowed query keywords for HR and Finance domains
        self.allowed_keywords = {
            'hr': [
                'employee', 'name', 'vacation', 'holiday', 'leave', 'days', 'time', 'off',
                'public', 'holidays', 'schedule', 'attendance', 'profile', 'information',
                'contact', 'phone', 'email', 'address', 'department', 'position', 'title',
                'hire', 'date', 'anniversary', 'birthday', 'emergency', 'contact'
            ],
            'finance': [
                'salary', 'annual', 'monthly', 'pay', 'payment', 'compensation', 'bonus',
                'raise', 'promotion', 'deduction', 'tax', 'benefits', 'insurance',
                'retirement', '401k', 'pension', 'expense', 'reimbursement', 'budget',
                'cost', 'revenue', 'profit', 'loss', 'financial', 'accounting'
            ],
            'general': [
                'what', 'how', 'when', 'where', 'who', 'why', 'which', 'is', 'are',
                'can', 'could', 'would', 'should', 'will', 'may', 'might', 'help',
                'show', 'tell', 'give', 'find', 'get', 'calculate', 'compute'
            ]
        }
    
    def validate_query(self, query: str) -> ValidationResult:
        """
        Validate user query input with comprehensive security checks.
        
        Args:
            query: The user's query string
            
        Returns:
            ValidationResult with validation status and sanitized input
        """
        if not query or not isinstance(query, str):
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                errors=["Query must be a non-empty string"],
                warnings=[],
                validation_level=self.validation_level
            )
        
        errors = []
        warnings = []
        sanitized_input = query.strip()
        
        # Length validation
        if len(sanitized_input) > self.max_query_length:
            errors.append(f"Query too long. Maximum length is {self.max_query_length} characters.")
            sanitized_input = sanitized_input[:self.max_query_length]
        
        if len(sanitized_input) < 3:
            errors.append("Query too short. Please provide more details.")
        
        # Check for malicious patterns
        malicious_detected = self._check_malicious_patterns(sanitized_input)
        if malicious_detected:
            errors.extend(malicious_detected)
            logger.warning(f"Malicious input detected: {sanitized_input}")
        
        # Check for allowed keywords (domain validation)
        if not self._validate_domain_keywords(sanitized_input):
            warnings.append("Query may not be related to HR or Finance domains.")
        
        # Sanitize input
        sanitized_input = self._sanitize_input(sanitized_input)
        
        # Additional security checks based on validation level
        if self.validation_level == ValidationLevel.HIGH:
            high_level_errors = self._high_level_validation(sanitized_input)
            errors.extend(high_level_errors)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_input=sanitized_input,
            errors=errors,
            warnings=warnings,
            validation_level=self.validation_level
        )
    
    def validate_employee_id(self, employee_id: str) -> ValidationResult:
        """
        Validate employee ID format.
        
        Args:
            employee_id: Employee ID string
            
        Returns:
            ValidationResult with validation status
        """
        if not employee_id or not isinstance(employee_id, str):
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                errors=["Employee ID must be a non-empty string"],
                warnings=[],
                validation_level=self.validation_level
            )
        
        sanitized_input = employee_id.strip().upper()
        errors = []
        warnings = []
        
        # Check format
        if not re.match(self.allowed_patterns[InputType.EMPLOYEE_ID], sanitized_input):
            errors.append("Employee ID must be in format EMP#### (e.g., EMP0001)")
        
        # Check for malicious patterns
        malicious_detected = self._check_malicious_patterns(sanitized_input)
        if malicious_detected:
            errors.extend(malicious_detected)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_input=sanitized_input,
            errors=errors,
            warnings=warnings,
            validation_level=self.validation_level
        )
    
    def _check_malicious_patterns(self, input_text: str) -> List[str]:
        """Check for malicious patterns in input text."""
        errors = []
        input_lower = input_text.lower()
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                errors.append(f"Potentially malicious input detected: {pattern}")
        
        return errors
    
    def _validate_domain_keywords(self, query: str) -> bool:
        """Validate that query contains relevant keywords for HR/Finance domains."""
        query_lower = query.lower()
        all_keywords = []
        
        for domain, keywords in self.allowed_keywords.items():
            all_keywords.extend(keywords)
        
        # Check if query contains at least one relevant keyword
        found_keywords = [keyword for keyword in all_keywords if keyword in query_lower]
        
        # Allow queries with common question words even if no domain keywords found
        question_words = ['what', 'how', 'when', 'where', 'who', 'why', 'which']
        has_question_word = any(word in query_lower for word in question_words)
        
        return len(found_keywords) > 0 or has_question_word
    
    def _sanitize_input(self, input_text: str) -> str:
        """Sanitize input text to prevent XSS and other attacks."""
        # HTML escape
        sanitized = html.escape(input_text)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized
    
    def _high_level_validation(self, input_text: str) -> List[str]:
        """Additional validation for high security level."""
        errors = []
        
        # Check for repeated characters (potential DoS)
        if len(input_text) > 10:
            char_counts = {}
            for char in input_text:
                char_counts[char] = char_counts.get(char, 0) + 1
                if char_counts[char] > len(input_text) * 0.7:  # 70% of input is same character
                    errors.append("Input contains too many repeated characters")
                    break
        
        # Check for suspicious character combinations
        suspicious_combos = ['../', '..\\', '<!--', '-->', '<?', '?>', '${', '}']
        for combo in suspicious_combos:
            if combo in input_text:
                errors.append(f"Suspicious character combination detected: {combo}")
        
        return errors
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics for monitoring."""
        return {
            "validation_level": self.validation_level.value,
            "max_input_length": self.max_input_length,
            "max_query_length": self.max_query_length,
            "malicious_patterns_count": len(self.malicious_patterns),
            "allowed_keywords_count": sum(len(keywords) for keywords in self.allowed_keywords.values())
        }

# Global validator instance
_validator = None

def get_validator(validation_level: ValidationLevel = ValidationLevel.MEDIUM) -> InputValidator:
    """Get or create input validator instance."""
    global _validator
    if _validator is None:
        _validator = InputValidator(validation_level)
    return _validator

def validate_user_input(input_text: str, input_type: InputType = InputType.QUERY) -> ValidationResult:
    """
    Convenience function to validate user input.
    
    Args:
        input_text: The input text to validate
        input_type: Type of input being validated
        
    Returns:
        ValidationResult with validation status
    """
    validator = get_validator()
    
    if input_type == InputType.EMPLOYEE_ID:
        return validator.validate_employee_id(input_text)
    elif input_type == InputType.QUERY:
        return validator.validate_query(input_text)
    else:
        # Default to query validation
        return validator.validate_query(input_text) 