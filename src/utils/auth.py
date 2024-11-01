from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
import base64
import datetime
from src.utils.logger import log_debug

""" LOGIC FOR API AUTH """

def load_private_key_from_file(file_path):
    """Load RSA private key from file"""
    with open(file_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def sign_message(private_key: rsa.RSAPrivateKey, message: str) -> str:
    """Sign a message using RSA-PSS with SHA256"""
    try:
        # Convert message to bytes
        message_bytes = message.encode('utf-8')
        
        # First hash the message with SHA256
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(message_bytes)
        message_hash = hasher.finalize()
        
        # Sign the hash with RSA-PSS
        signature = private_key.sign(
            message_hash,  # Sign the hash, not the raw message
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Encode signature in base64
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        log_debug(f"Signing error: {e}")
        raise

def get_auth_headers(method: str, path: str, private_key_path: str, access_key: str) -> dict:
    """Generate authentication headers for Kalshi API"""
    # Get current timestamp in milliseconds
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    
    # Create the message string to sign (timestamp + method + path)
    # Ensure path is clean without query parameters
    clean_path = path.split('?')[0]
    message = f"{timestamp}{method}{clean_path}"
    
    # Load private key and sign message
    private_key = load_private_key_from_file(private_key_path)
    signature = sign_message(private_key, message)
    #print(signature, private_key)
    # Return headers
    return {
        'KALSHI-ACCESS-KEY': access_key,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }