import os
import subprocess
import sys
from pathlib import Path

def setup_bridger():
    print("🛰️ Initializing Bridger Environment...")
    
    # 1. Key Generation (using RSA for encryption)
    keys_path = Path.home() / ".ssh" / "bridger_keys"
    keys_path.mkdir(exist_ok=True, parents=True)
    priv_key = keys_path / "bridger_rsa"
    
    if not priv_key.exists():
        print("🔑 Generating RSA identity...")
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "2048", 
            "-f", str(priv_key), "-N", "", "-q"
        ], check=True)
        os.chmod(priv_key, 0o600)
        print(f"✅ RSA key generated at {priv_key}")
    else:
        print("✅ Bridger RSA identity already exists.")

    # 2. Public Key for sharing
    with open(str(priv_key) + ".pub", "r") as f:
        pub_key = f.read().strip()
        print(f"\n📬 YOUR BRIDGER ADDRESS:\n{pub_key}\n")

    # 3. Create necessary folders
    base_path = Path("/Users/hamednejat/workspace/Computational/bridger")
    for folder in ["received", "read", "plans"]:
        (base_path / folder).mkdir(exist_ok=True, parents=True)
    
    print("✅ Local workspace folders initialized.")
    print("\nNext Steps:")
    print("1. Share your address with your partner.")
    print("2. Get their address and save it to a .pub file.")
    print("3. Clone your private GitHub relay repo into 'workspace/Computational/bridger/relay_mailbox'.")

if __name__ == "__main__":
    setup_bridger()
