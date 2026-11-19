# Tsukyo Coin (TKC) — Educational Testnet Node v0.2.0

**Status: experimental single-node testnet milestone. TKC here has no monetary value.** This is not a production cryptocurrency, not audited, and not yet a decentralized peer-to-peer network. Do not use real funds or reuse real wallet keys.

## Implemented in v0.2
- Ed25519 wallet key generation and TKC1 addresses.
- Signed transactions with sender, recipient, amount, fee, and sequential nonce.
- SHA-256 proof-of-work blocks and previous-block hash linking.
- Local mempool, mining rewards, balance accounting, and chain verification.
- Mining issuance capped at the proposed 8,000,000 TKC mining allocation.
- Atomic chain-file writes and basic tamper-detection tests.

## Not implemented yet
- Peer-to-peer networking, peer discovery, fork choice/reorgs, difficulty adjustment, persistent transaction index, secure encrypted wallet storage, seed phrase recovery, mobile wallet integration, Firebase auth/backend, explorer/API, independent security audit, and production hardening.
- The 21,000,000 maximum and other allocation buckets are still tokenomics proposals. Only the 8,000,000 mining cap is enforced in this milestone; genesis/treasury/ecosystem/reserve issuance is not implemented.
- This is a new educational prototype, not a Bitcoin Core fork. Bitcoin Core source is large consensus-critical software; changing its parameters alone would not create a safe TKC chain.

## Run (Android Termux / Linux)
```sh
pkg update && pkg install python
pip install -r requirements.txt
python tkc.py wallet-new alice
python tkc.py wallet-new bob
python tkc.py mine alice
python tkc.py balance alice
python tkc.py send alice <BOB_TKC1_ADDRESS> 1
python tkc.py mine bob
python tkc.py status
python tkc.py verify
python -m unittest -v
```

Wallet files are saved under `wallets/`. Treat them as secret even though this is only a testnet. Back them up securely; never upload private key files to GitHub. Chain data is under `data/`.

## Protocol parameters (prototype only)
- Network: `TKC-EDU-TESTNET`
- Hash: SHA-256
- Signature: Ed25519
- Difficulty: 3 leading hexadecimal zeroes (fixed for local tests)
- Block reward: 1 TKC
- Mining issuance cap: 8,000,000 TKC
- Proposed max supply: 21,000,000 TKC (not yet fully enforced)
