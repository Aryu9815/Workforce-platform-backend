from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# 1. Generate EC key pair (P-256) — REQUIRED by WebPush
private_key = ec.generate_private_key(ec.SECP256R1())

# 2. Export private key (raw bytes)
raw_private = private_key.private_numbers().private_value.to_bytes(32, "big")
private_key_b64 = base64.urlsafe_b64encode(raw_private).rstrip(b"=").decode("utf-8")

# 3. Export public key in uncompressed format (04 + X + Y)
public_key = private_key.public_key().public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint
)
public_key_b64 = base64.urlsafe_b64encode(public_key).rstrip(b"=").decode("utf-8")

print("PUBLIC KEY:\n", public_key_b64)
print("\nPRIVATE KEY:\n", private_key_b64)