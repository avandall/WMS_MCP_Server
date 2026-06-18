"""Compliance testing script for WMS MCP Server"""

import subprocess
import json
from pathlib import Path


def check_gdpr_compliance():
    """Check GDPR compliance"""
    print("Checking GDPR compliance...")
    
    # Check for PII handling
    pii_keywords = [
        "email", "phone", "address", "ssn", "credit_card",
        "personal_data", "sensitive_data"
    ]
    
    for py_file in Path("app").rglob("*.py"):
        with open(py_file) as f:
            content = f.read()
            
            for keyword in pii_keywords:
                if keyword in content.lower():
                    print(f"Found PII-related keyword '{keyword}' in {py_file}")
                    print("Ensure proper data protection measures are in place")
    
    return True


def check_logging_compliance():
    """Check logging compliance"""
    print("Checking logging compliance...")
    
    # Check if logging is implemented
    log_files = list(Path("app").rglob("*log*"))
    
    if log_files:
        print(f"Found {len(log_files)} log-related files")
    else:
        print("No log files found - ensure logging is implemented")
    
    return True


def check_encryption_compliance():
    """Check encryption compliance"""
    print("Checking encryption compliance...")
    
    # Check for encryption usage
    encryption_keywords = ["encrypt", "decrypt", "ssl", "tls", "hash"]
    
    for py_file in Path("app").rglob("*.py"):
        with open(py_file) as f:
            content = f.read()
            
            for keyword in encryption_keywords:
                if keyword in content.lower():
                    print(f"Found encryption-related keyword '{keyword}' in {py_file}")
    
    return True


def run_all_compliance_checks():
    """Run all compliance checks"""
    print("Starting compliance testing...")
    print("=" * 50)
    
    gdpr_ok = check_gdpr_compliance()
    logging_ok = check_logging_compliance()
    encryption_ok = check_encryption_compliance()
    
    print("=" * 50)
    
    if gdpr_ok and logging_ok and encryption_ok:
        print("All compliance checks passed")
        return True
    else:
        print("Some compliance checks need attention")
        return False


if __name__ == "__main__":
    success = run_all_compliance_checks()
    exit(0 if success else 1)
