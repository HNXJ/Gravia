import os
import sys
import json
import time
import pickle
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.fernet import Fernet
except ImportError:
    print("cryptography library not found. Please install: pip install cryptography")
    sys.exit(1)

class BridgerMod:
    """
    Safe Peer-to-Peer messaging module.
    Uses Git as a relay and RSA + Fernet for end-to-end encryption.
    """
    def __init__(self, relay_url: str, partner_pubkey_path: Optional[str] = None):
        self.relay_url = relay_url
        self.base_path = Path("/Users/hamednejat/workspace/Computational/bridger")
        self.mailbox_path = self.base_path / "relay_mailbox"
        self.keys_path = Path.home() / ".ssh" / "bridger_keys"
        self.keys_path.mkdir(exist_ok=True, parents=True)
        
        self.private_key_file = self.keys_path / "bridger_rsa"
        self.public_key_file = self.keys_path / "bridger_rsa.pub"
        
        # 1. Initialize Identity
        self._init_identity()
        
        # 2. Setup Relay
        self._init_relay()
        
        # 3. Load Partner
        self.partner_pubkey = None
        if partner_pubkey_path and os.path.exists(partner_pubkey_path):
            with open(partner_pubkey_path, "rb") as f:
                self.partner_pubkey = serialization.load_ssh_public_key(f.read())
        
        # Queues
        self.received_queue = []

    def _init_identity(self):
        """Generates RSA keys for encryption if they don't exist."""
        if not self.private_key_file.exists():
            print("🔑 Generating Bridger RSA identity...")
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            with open(self.private_key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            public_key = private_key.public_key()
            with open(self.public_key_file, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.OpenSSH,
                    format=serialization.PublicFormat.OpenSSH
                ))
            os.chmod(self.private_key_file, 0o600)
        
        with open(self.private_key_file, "rb") as f:
            self.my_private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        # My Identity Hash (for folder naming)
        with open(self.public_key_file, "rb") as f:
            pub_bytes = f.read()
            self.my_id_hash = hashlib.sha256(pub_bytes).hexdigest()[:12]

    def _init_relay(self):
        """Clones or updates the Git relay repo."""
        if not self.mailbox_path.exists():
            print(f"📂 Cloning relay mailbox: {self.relay_url}")
            subprocess.run(["git", "clone", self.relay_url, str(self.mailbox_path)], check=True)
        else:
            subprocess.run(["git", "-C", str(self.mailbox_path), "pull", "--rebase"], check=True)
        
        # Create inbox for self
        self.inbox_path = self.mailbox_path / f"inbox_{self.my_id_hash}"
        self.inbox_path.mkdir(exist_ok=True)

    def get_my_address(self) -> str:
        """Returns the public key string to share with partner."""
        with open(self.public_key_file, "r") as f:
            return f.read().strip()

    def send(self, mode: str, msg: Any, partner_id_hash: Optional[str] = None):
        """
        Encrypts and sends a message/file to the partner.
        mode: "text", "file", "url", "markdown", "p"
        """
        if not self.partner_pubkey:
            raise ValueError("Partner public key not loaded. Cannot encrypt.")
        
        print(f"📤 Sending {mode} message...")
        
        # 1. Prepare Payload
        if mode == "text" or mode == "url" or mode == "markdown":
            data = msg.encode()
        elif mode == "file" or mode == "p":
            with open(msg, "rb") as f:
                data = f.read()
        else:
            data = pickle.dumps(msg)

        # 2. Hybrid Encryption (Fernet for data, RSA for Fernet key)
        sym_key = Fernet.generate_key()
        f = Fernet(sym_key)
        encrypted_data = f.encrypt(data)
        
        encrypted_sym_key = self.partner_pubkey.encrypt(
            sym_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 3. Wrap in Envelope
        envelope = {
            "mode": mode,
            "sender": self.my_id_hash,
            "timestamp": time.time(),
            "encrypted_sym_key": encrypted_sym_key.hex(),
            "payload": encrypted_data.hex(),
            "filename": os.path.basename(msg) if mode in ["file", "p"] else f"msg_{int(time.time())}"
        }
        
        # 4. Push to Relay
        target_inbox = self.mailbox_path / f"inbox_{partner_id_hash}" if partner_id_hash else self.mailbox_path / "shared_inbox"
        target_inbox.mkdir(exist_ok=True)
        
        env_file = target_inbox / f"{envelope['filename']}.bridger"
        with open(env_file, "w") as f:
            json.dump(envelope, f)
            
        subprocess.run(["git", "-C", str(self.mailbox_path), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.mailbox_path), "commit", "-m", f"send {mode} from {self.my_id_hash}"], check=True)
        subprocess.run(["git", "-C", str(self.mailbox_path), "push"], check=True)
        print("✅ Message pushed to relay.")

    def check(self) -> List[str]:
        """Pulls from Git and lists new messages."""
        subprocess.run(["git", "-C", str(self.mailbox_path), "pull", "--rebase"], check=True)
        new_messages = list(self.inbox_path.glob("*.bridger"))
        
        summary = []
        for msg_file in new_messages:
            summary.append(msg_file.name)
            # Move to local 'received' to mark as received but not read
            received_dir = self.base_path / "received"
            received_dir.mkdir(exist_ok=True)
            os.rename(msg_file, received_dir / msg_file.name)
            
        print(f"📬 Checked: Found {len(summary)} new messages.")
        return summary

    def read(self) -> Dict[str, Any]:
        """Pops and decrypts the front of the queue (Text > File)."""
        received_dir = self.base_path / "received"
        messages = list(received_dir.glob("*.bridger"))
        if not messages:
            return None
        
        # Priority logic: find first text-like message
        selected_msg = messages[0]
        for m in messages:
            with open(m, "r") as f:
                env = json.load(f)
                if env["mode"] in ["text", "markdown", "url"]:
                    selected_msg = m
                    break
        
        with open(selected_msg, "r") as f:
            envelope = json.load(f)
            
        # Decrypt sym key
        encrypted_sym_key = bytes.fromhex(envelope["encrypted_sym_key"])
        sym_key = self.my_private_key.decrypt(
            encrypted_sym_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt payload
        f = Fernet(sym_key)
        decrypted_data = f.decrypt(bytes.fromhex(envelope["payload"]))
        
        # Cleanup
        read_dir = self.base_path / "read"
        read_dir.mkdir(exist_ok=True)
        os.rename(selected_msg, read_dir / selected_msg.name)
        
        result = {
            "mode": envelope["mode"],
            "data": decrypted_data.decode() if envelope["mode"] in ["text", "markdown", "url"] else decrypted_data,
            "filename": envelope["filename"],
            "sender": envelope["sender"]
        }
        return result

    def reply(self, to_filename: str, mode: str, msg: Any, partner_id_hash: str):
        """Replies to a specific message."""
        # Simple implementation: just a send with metadata link
        print(f"💬 Replying to {to_filename}...")
        self.send(mode, msg, partner_id_hash)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bridger Safe Messaging CLI")
    parser.add_argument("--address", action="store_true", help="Show my Bridger address (public key)")
    parser.add_argument("--check", action="store_true", help="Check for new messages")
    parser.add_argument("--relay", type=str, help="Relay Git URL (required for initialization)")
    
    args = parser.parse_args()
    
    if args.address:
        # Dummy init to get path
        bridger = BridgerMod(relay_url="")
        print("\n📫 YOUR BRIDGER ADDRESS (PUBLIC KEY):")
        print(bridger.get_my_address())
        print(f"\nYour ID Hash: {bridger.my_id_hash}")
    
    elif args.check:
        if not args.relay:
            print("Error: --relay <url> is required to check messages.")
        else:
            bridger = BridgerMod(relay_url=args.relay)
            bridger.check()
    
    else:
        parser.print_help()
