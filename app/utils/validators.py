"""
Validation utility functions.
"""
import re
from typing import Tuple, Optional


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    Returns (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 255:
        return False, "Email too long (max 255 characters)"
    
    return True, None


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format.
    Returns (is_valid, error_message)
    """
    if not phone:
        return True, None  # Phone is optional
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    # Basic phone validation (at least 10 digits)
    if not re.match(r'^\+?[\d]{10,15}$', cleaned):
        return False, "Invalid phone number format"
    
    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password too long (max 128 characters)"
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-=\[\]\\;\'/`~]', password):
        return False, "Password must contain at least one special character"
    
    # Check for common weak passwords
    common_passwords = [
        'password', '123456', 'qwerty', 'abc123', 'letmein',
        'welcome', 'admin', 'login', 'master'
    ]
    
    if password.lower() in common_passwords:
        return False, "Password is too common"
    
    return True, None
