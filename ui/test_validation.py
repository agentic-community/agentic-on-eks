#!/usr/bin/env python3
"""
Test script for input validation functionality.
Demonstrates various validation scenarios and security measures.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from input_validation import validate_user_input, InputType, ValidationLevel, get_validator

def test_validation_scenarios():
    """Test various validation scenarios."""
    
    print("🔒 Input Validation Test Suite")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        # Valid queries
        ("What is the name of employee EMP0002?", "Valid HR query"),
        ("What is the annual salary of EMP0003?", "Valid Finance query"),
        ("How many vacation days does EMP0001 have left?", "Valid HR query with employee ID"),
        
        # Malicious inputs
        ("<script>alert('xss')</script>", "XSS attack attempt"),
        ("SELECT * FROM employees", "SQL injection attempt"),
        ("../etc/passwd", "Path traversal attempt"),
        ("rm -rf /", "Command injection attempt"),
        ("javascript:alert('xss')", "JavaScript injection"),
        
        # Invalid employee IDs
        ("What is the name of employee ABC123?", "Invalid employee ID format"),
        ("What is the name of employee EMP999?", "Invalid employee ID format"),
        
        # Too long queries
        ("A" * 600, "Query too long"),
        
        # Too short queries
        ("Hi", "Query too short"),
        
        # Suspicious patterns
        ("admin password", "Suspicious keywords"),
        ("root sudo", "Suspicious keywords"),
        ("delete all", "Suspicious keywords"),
        
        # Normal but potentially suspicious
        ("What is the system password?", "Suspicious but valid format"),
        ("How do I access the admin panel?", "Suspicious but valid format"),
    ]
    
    print(f"Testing {len(test_cases)} scenarios...\n")
    
    for query, description in test_cases:
        print(f"📝 Test: {description}")
        print(f"Query: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        result = validate_user_input(query, InputType.QUERY)
        
        if result.is_valid:
            print("✅ VALID")
        else:
            print("❌ INVALID")
            print("Errors:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("⚠️ Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        print(f"Sanitized: {result.sanitized_input[:50]}{'...' if len(result.sanitized_input) > 50 else ''}")
        print("-" * 50)

def test_employee_id_validation():
    """Test employee ID validation specifically."""
    
    print("\n👤 Employee ID Validation Tests")
    print("=" * 50)
    
    employee_ids = [
        ("EMP0001", "Valid employee ID"),
        ("EMP9999", "Valid employee ID"),
        ("ABC123", "Invalid format"),
        ("emp0001", "Invalid case"),
        ("EMP001", "Too short"),
        ("EMP00001", "Too long"),
        ("EMP0001<script>", "With malicious content"),
    ]
    
    for emp_id, description in employee_ids:
        print(f"📝 Test: {description}")
        print(f"Employee ID: {emp_id}")
        
        result = validate_user_input(emp_id, InputType.EMPLOYEE_ID)
        
        if result.is_valid:
            print("✅ VALID")
        else:
            print("❌ INVALID")
            print("Errors:")
            for error in result.errors:
                print(f"  • {error}")
        
        print(f"Sanitized: {result.sanitized_input}")
        print("-" * 30)

def test_validation_levels():
    """Test different validation levels."""
    
    print("\n🔐 Validation Level Tests")
    print("=" * 50)
    
    test_query = "A" * 100  # Query with repeated characters
    
    for level in ValidationLevel:
        print(f"Testing {level.value.upper()} security level:")
        
        # Create validator with specific level
        validator = get_validator(level)
        result = validator.validate_query(test_query)
        
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        print()

def show_validation_stats():
    """Show validation statistics."""
    
    print("\n📊 Validation Statistics")
    print("=" * 50)
    
    validator = get_validator()
    stats = validator.get_validation_stats()
    
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

def main():
    """Run all validation tests."""
    
    print("🚀 Starting Input Validation Test Suite")
    print("This demonstrates the security features implemented for Issue #12")
    print()
    
    # Run tests
    test_validation_scenarios()
    test_employee_id_validation()
    test_validation_levels()
    show_validation_stats()
    
    print("\n✅ Test suite completed!")
    print("\nThis validation system implements:")
    print("• SQL Injection protection")
    print("• XSS attack prevention")
    print("• Command injection detection")
    print("• Path traversal protection")
    print("• Input length validation")
    print("• Domain-specific keyword validation")
    print("• Input sanitization")
    print("• Multiple security levels")

if __name__ == "__main__":
    main() 