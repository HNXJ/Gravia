---
name: bridger-module
description: Safe peer-to-peer messaging using Git-relays and RSA encryption.
---

# Bridger Module

This repository provides the core logic for the **Bridger** messaging system.

## Setup
1. Clone the repository.
2. Run `python setup.py` to initialize keys and folders.
3. Share your address (RSA Public Key) with your partner.

## Usage
Refer to `bridger.py` for the CLI and API.
- Get Address: `python bridger.py --address`
- Check Mail: `python bridger.py --check --relay <git_url>`
