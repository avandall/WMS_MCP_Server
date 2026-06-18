"""Security audit script for WMS MCP Server"""

import os
import re
from pathlib import Path


class SecurityAuditor:
    """Security auditor for WMS MCP Server"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues = []
    
    def check_hardcoded_secrets(self):
        """Check for hardcoded secrets in code"""
        print("Checking for hardcoded secrets...")
        
        patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or ".venv" in str(py_file):
                continue
            
            with open(py_file) as f:
                content = f.read()
                
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        self.issues.append({
                            "file": str(py_file),
                            "issue": "Potential hardcoded secret",
                            "pattern": pattern
                        })
    
    def check_insecure_deserialization(self):
        """Check for insecure deserialization"""
        print("Checking for insecure deserialization...")
        
        dangerous_functions = [
            "pickle.loads",
            "pickle.load",
            "yaml.load",
        ]
        
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or ".venv" in str(py_file):
                continue
            
            with open(py_file) as f:
                content = f.read()
                
                for func in dangerous_functions:
                    if func in content:
                        self.issues.append({
                            "file": str(py_file),
                            "issue": f"Use of {func} (potential security risk)",
                            "function": func
                        })
    
    def check_sql_injection_risks(self):
        """Check for potential SQL injection risks"""
        print("Checking for SQL injection risks...")
        
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or ".venv" in str(py_file):
                continue
            
            with open(py_file) as f:
                content = f.read()
                
                # Check for string concatenation in SQL queries
                if re.search(r'execute\s*\([^)]*\+', content, re.IGNORECASE):
                    self.issues.append({
                        "file": str(py_file),
                        "issue": "Potential SQL injection via string concatenation"
                    })
    
    def check_debug_mode(self):
        """Check for debug mode enabled in production"""
        print("Checking for debug mode...")
        
        env_files = [".env", ".env.production", ".env.staging"]
        
        for env_file in env_files:
            env_path = self.project_root / env_file
            if env_path.exists():
                with open(env_path) as f:
                    content = f.read()
                    
                    if "DEBUG=True" in content or "DEBUG=true" in content:
                        self.issues.append({
                            "file": str(env_path),
                            "issue": "Debug mode enabled (security risk)"
                        })
    
    def run_audit(self):
        """Run complete security audit"""
        print("Starting security audit...")
        print("=" * 50)
        
        self.check_hardcoded_secrets()
        self.check_insecure_deserialization()
        self.check_sql_injection_risks()
        self.check_debug_mode()
        
        print("=" * 50)
        
        if self.issues:
            print(f"Found {len(self.issues)} security issues:")
            for issue in self.issues:
                print(f"\nFile: {issue['file']}")
                print(f"Issue: {issue['issue']}")
                if 'pattern' in issue:
                    print(f"Pattern: {issue['pattern']}")
                if 'function' in issue:
                    print(f"Function: {issue['function']}")
            return False
        else:
            print("No security issues found")
            return True


if __name__ == "__main__":
    auditor = SecurityAuditor()
    success = auditor.run_audit()
    exit(0 if success else 1)
