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


def validate_phone(phone: str, country_code: str = "US") -> Tuple[bool, Optional[str]]:
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


def validate_slug(slug: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL slug format.
    Returns (is_valid, error_message)
    """
    if not slug:
        return False, "Slug is required"
    
    # Slug pattern: lowercase letters, numbers, hyphens
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    
    if not re.match(pattern, slug):
        return False, "Slug can only contain lowercase letters, numbers, and hyphens"
    
    if len(slug) > 100:
        return False, "Slug too long (max 100 characters)"
    
    return True, None


def validate_currency_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate currency code (ISO 4217).
    Returns (is_valid, error_message)
    """
    valid_currencies = {
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY',
        'HKD', 'NZD', 'SEK', 'KRW', 'SGD', 'NOK', 'MXN', 'INR',
        'RUB', 'ZAR', 'TRY', 'BRL', 'TWD', 'DKK', 'PLN', 'THB',
        'IDR', 'HUF', 'CZK', 'ILS', 'CLP', 'PHP', 'AED', 'COP',
        'SAR', 'MYR', 'RON', 'AFN', 'ALL', 'DZD', 'AOA', 'ARS',
    }
    
    if not code:
        return False, "Currency code is required"
    
    if code.upper() not in valid_currencies:
        return False, f"Invalid currency code: {code}"
    
    return True, None


def validate_hex_color(color: str) -> Tuple[bool, Optional[str]]:
    """
    Validate hex color code.
    Returns (is_valid, error_message)
    """
    if not color:
        return True, None  # Color is optional
    
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    
    if not re.match(pattern, color):
        return False, "Invalid hex color format (use #RRGGBB or #RGB)"
    
    return True, None


def validate_timezone(timezone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate timezone string.
    Returns (is_valid, error_message)
    """
    import pytz
    
    if not timezone:
        return False, "Timezone is required"
    
    try:
        pytz.timezone(timezone)
        return True, None
    except pytz.exceptions.UnknownTimeZoneError:
        return False, f"Unknown timezone: {timezone}"


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.
    Returns (is_valid, error_message)
    """
    if not url:
        return True, None  # URL is optional
    
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    
    if not re.match(pattern, url, re.IGNORECASE):
        return False, "Invalid URL format"
    
    if len(url) > 2000:
        return False, "URL too long (max 2000 characters)"
    
    return True, None


def validate_file_extension(filename: str, allowed_extensions: set) -> Tuple[bool, Optional[str]]:
    """
    Validate file extension.
    Returns (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if ext not in allowed_extensions:
        return False, f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


def validate_ip_address(ip: str) -> Tuple[bool, Optional[str]]:
    """
    Validate IP address (IPv4 or IPv6).
    Returns (is_valid, error_message)
    """
    if not ip:
        return True, None  # IP is optional
    
    # IPv4 pattern
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    
    if re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip):
        return True, None
    
    return False, "Invalid IP address format"
