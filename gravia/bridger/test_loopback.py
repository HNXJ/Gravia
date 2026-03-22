from bridger import BridgerMod
import os
import shutil

def main():
    relay_url = "/Users/hamednejat/workspace/Computational/bridger/test_relay"
    
    # 1. Setup Sender (and Receiver in this loopback)
    print("🚀 Initializing Bridger Loopback Test...")
    bridger = BridgerMod(relay_url=relay_url)
    
    # In loopback, partner is self
    my_address_file = str(bridger.public_key_file)
    bridger.partner_pubkey_path = my_address_file
    with open(my_address_file, "rb") as f:
        from cryptography.hazmat.primitives import serialization
        bridger.partner_pubkey = serialization.load_ssh_public_key(f.read())
    
    partner_hash = bridger.my_id_hash
    
    # 2. Send Message
    test_msg = "Hello from Bridger Loopback! The hierarchy training is done."
    bridger.send(mode="text", msg=test_msg, partner_id_hash=partner_hash)
    
    # 3. Check for Messages
    print("\n📫 Checking for messages...")
    new_msgs = bridger.check()
    if new_msgs:
        print(f"Found: {new_msgs}")
        
        # 4. Read Message
        print("\n📖 Reading message...")
        content = bridger.read()
        print(f"Decrypted Content: {content['data']}")
        
        if content['data'] == test_msg:
            print("\n✅ Loopback Test Passed: Encryption and Relay successful!")
        else:
            print("\n❌ Loopback Test Failed: Content mismatch.")
    else:
        print("\n❌ Loopback Test Failed: No messages found in relay.")

if __name__ == "__main__":
    # Clean up old test data if exists
    mailbox = "/Users/hamednejat/workspace/Computational/bridger/relay_mailbox"
    if os.path.exists(mailbox):
        shutil.rmtree(mailbox)
    
    main()
