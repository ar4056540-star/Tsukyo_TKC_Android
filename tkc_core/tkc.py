#!/usr/bin/env python3
"""Tsukyo Coin (TKC) educational testnet node v0.2.0.

This is an experimental, single-node testnet. Coins have no monetary value.
Not audited, not suitable for real funds, and not a decentralized network.
"""
from __future__ import annotations
import argparse, hashlib, json, os, secrets, sys, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CHAIN_FILE = DATA / "chain.json"
WALLETS = ROOT / "wallets"
NETWORK = "TKC-EDU-TESTNET"
VERSION = "0.2.0"
MAX_SUPPLY = 21_000_000
MINING_ALLOCATION = 8_000_000
BLOCK_REWARD = 1
DIFFICULTY = 3
MAX_TX_PER_BLOCK = 100


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> int:
    return int(time.time())


def address_for(pub_hex: str) -> str:
    return "TKC1" + sha(bytes.fromhex(pub_hex))[:40]


def create_wallet(name: str) -> Path:
    WALLETS.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in name if c.isalnum() or c in "-_")[:40]
    if not safe:
        raise ValueError("Wallet name must contain letters or numbers")
    path = WALLETS / f"{safe}.json"
    if path.exists():
        raise ValueError(f"Wallet already exists: {path.name}")
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()).hex()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    record = {"network": NETWORK, "name": safe, "private_key_hex": private, "public_key_hex": public, "address": address_for(public)}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    try: os.chmod(path, 0o600)
    except OSError: pass
    return path


def load_wallet(name: str) -> dict:
    path = WALLETS / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("network") != NETWORK or address_for(data["public_key_hex"]) != data["address"]:
        raise ValueError("Wallet file invalid or belongs to another network")
    return data


def tx_signing_payload(tx: dict) -> dict:
    return {k: tx[k] for k in ("sender", "recipient", "amount", "fee", "nonce", "public_key")}


def make_transaction(wallet: dict, recipient: str, amount: int, fee: int, nonce: int) -> dict:
    if not recipient.startswith("TKC1") or len(recipient) != 44:
        raise ValueError("Recipient must be a TKC1 address")
    if amount <= 0 or fee < 0:
        raise ValueError("Amount must be positive and fee cannot be negative")
    tx = {"sender": wallet["address"], "recipient": recipient, "amount": amount, "fee": fee,
          "nonce": nonce, "public_key": wallet["public_key_hex"]}
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(wallet["private_key_hex"]))
    tx["signature"] = key.sign(canonical(tx_signing_payload(tx))).hex()
    tx["txid"] = sha(canonical(tx))
    return tx


def verify_transaction(tx: dict) -> bool:
    try:
        if tx["sender"] != address_for(tx["public_key"]): return False
        if not tx["recipient"].startswith("TKC1") or len(tx["recipient"]) != 44: return False
        if not isinstance(tx["amount"], int) or not isinstance(tx["fee"], int) or not isinstance(tx["nonce"], int): return False
        if tx["amount"] <= 0 or tx["fee"] < 0 or tx["nonce"] < 0: return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(tx["public_key"])).verify(bytes.fromhex(tx["signature"]), canonical(tx_signing_payload(tx)))
        return tx.get("txid") == sha(canonical({k: v for k, v in tx.items() if k != "txid"}))
    except Exception:
        return False


def block_hash(block: dict) -> str:
    return sha(canonical({k: v for k, v in block.items() if k != "hash"}))


def genesis() -> dict:
    b = {"height": 0, "timestamp": now(), "previous_hash": "0" * 64, "nonce": 0,
         "miner": "GENESIS", "transactions": [], "reward": 0}
    b["hash"] = block_hash(b)
    return {"network": NETWORK, "version": VERSION, "max_supply": MAX_SUPPLY,
            "mining_allocation": MINING_ALLOCATION, "difficulty": DIFFICULTY,
            "blocks": [b], "mempool": []}


def load_chain() -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    if not CHAIN_FILE.exists():
        c = genesis(); save_chain(c); return c
    c = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    if c.get("network") != NETWORK: raise ValueError("Wrong network file")
    ok, reason = validate_chain(c)
    if not ok: raise ValueError(f"Stored chain is invalid: {reason}")
    return c


def save_chain(c: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = CHAIN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(c, indent=2), encoding="utf-8")
    os.replace(tmp, CHAIN_FILE)


def chain_state(blocks: list[dict]) -> tuple[dict, dict, int]:
    balances: dict[str, int] = {}
    nonces: dict[str, int] = {}
    minted = 0
    for block in blocks[1:]:
        coinbase = block["transactions"][0]
        balances[coinbase["recipient"]] = balances.get(coinbase["recipient"], 0) + coinbase["amount"]
        minted += coinbase["amount"]
        for tx in block["transactions"][1:]:
            balances[tx["sender"]] -= tx["amount"] + tx["fee"]
            balances[tx["recipient"]] = balances.get(tx["recipient"], 0) + tx["amount"]
            balances[coinbase["recipient"]] += tx["fee"]
            nonces[tx["sender"]] = tx["nonce"]
    return balances, nonces, minted


def validate_chain(c: dict) -> tuple[bool, str]:
    try:
        blocks = c["blocks"]
        if not blocks: return False, "empty chain"
        if c.get("network") != NETWORK or c.get("difficulty") != DIFFICULTY: return False, "network parameters mismatch"
        g = genesis()
        # Genesis timestamp is fixed by stored genesis; validate its structure/hash, not current time.
        first = blocks[0]
        if first["height"] != 0 or first["previous_hash"] != "0" * 64 or first["hash"] != block_hash(first): return False, "bad genesis"
        balances: dict[str, int] = {}; nonces: dict[str, int] = {}; minted = 0
        for i, b in enumerate(blocks[1:], 1):
            if b["height"] != i or b["previous_hash"] != blocks[i-1]["hash"]: return False, f"link/height error at {i}"
            if b["hash"] != block_hash(b) or not b["hash"].startswith("0" * DIFFICULTY): return False, f"proof-of-work/hash error at {i}"
            txs = b["transactions"]
            if not txs or len(txs) > MAX_TX_PER_BLOCK + 1: return False, f"transaction count error at {i}"
            cb = txs[0]
            if set(cb) != {"recipient", "amount", "kind"} or cb["kind"] != "coinbase" or cb["amount"] != BLOCK_REWARD: return False, f"bad coinbase at {i}"
            if minted + cb["amount"] > MINING_ALLOCATION: return False, "mining allocation exceeded"
            minted += cb["amount"]
            balances[cb["recipient"]] = balances.get(cb["recipient"], 0) + cb["amount"]
            seen = set()
            for tx in txs[1:]:
                if not verify_transaction(tx): return False, f"invalid signature/transaction at block {i}"
                if tx["txid"] in seen: return False, "duplicate transaction in block"
                seen.add(tx["txid"])
                sender = tx["sender"]
                if tx["nonce"] != nonces.get(sender, 0) + 1: return False, "bad transaction nonce"
                if balances.get(sender, 0) < tx["amount"] + tx["fee"]: return False, "overspend"
                balances[sender] -= tx["amount"] + tx["fee"]
                balances[tx["recipient"]] = balances.get(tx["recipient"], 0) + tx["amount"]
                balances[cb["recipient"]] += tx["fee"]
                nonces[sender] = tx["nonce"]
        return True, f"valid; height={len(blocks)-1}; mined={minted} TKC"
    except Exception as e:
        return False, f"malformed chain: {e}"


def current_nonce(c: dict, address: str) -> int:
    _, nonces, _ = chain_state(c["blocks"])
    for tx in c.get("mempool", []):
        if tx["sender"] == address: nonces[address] = max(nonces.get(address, 0), tx["nonce"])
    return nonces.get(address, 0)


def submit_tx(c: dict, tx: dict) -> None:
    if not verify_transaction(tx): raise ValueError("Signature or transaction invalid")
    if any(x["txid"] == tx["txid"] for x in c["mempool"]): raise ValueError("Transaction already pending")
    balances, _, _ = chain_state(c["blocks"])
    pending_spend = sum(x["amount"] + x["fee"] for x in c["mempool"] if x["sender"] == tx["sender"])
    if tx["nonce"] != current_nonce(c, tx["sender"]) + 1: raise ValueError("Incorrect nonce")
    if balances.get(tx["sender"], 0) - pending_spend < tx["amount"] + tx["fee"]: raise ValueError("Insufficient testnet balance")
    c["mempool"].append(tx); save_chain(c)


def mine(c: dict, miner: str) -> dict:
    if not miner.startswith("TKC1") or len(miner) != 44: raise ValueError("Miner must be a TKC1 wallet address")
    _, _, minted = chain_state(c["blocks"])
    if minted + BLOCK_REWARD > MINING_ALLOCATION: raise ValueError("Mining allocation exhausted")
    selected = c["mempool"][:MAX_TX_PER_BLOCK]
    # Build candidate state in order; discard transactions that fail against preceding valid ones.
    balances, nonces, _ = chain_state(c["blocks"])
    accepted = []
    for tx in selected:
        sender = tx["sender"]
        if verify_transaction(tx) and tx["nonce"] == nonces.get(sender, 0) + 1 and balances.get(sender, 0) >= tx["amount"] + tx["fee"]:
            balances[sender] -= tx["amount"] + tx["fee"]
            balances[tx["recipient"]] = balances.get(tx["recipient"], 0) + tx["amount"]
            nonces[sender] = tx["nonce"]
            accepted.append(tx)
    txs = [{"recipient": miner, "amount": BLOCK_REWARD, "kind": "coinbase"}] + accepted
    prev = c["blocks"][-1]
    b = {"height": prev["height"] + 1, "timestamp": now(), "previous_hash": prev["hash"],
         "nonce": 0, "miner": miner, "transactions": txs, "reward": BLOCK_REWARD}
    target = "0" * DIFFICULTY
    while True:
        h = block_hash(b)
        if h.startswith(target): b["hash"] = h; break
        b["nonce"] += 1
    c["blocks"].append(b)
    accepted_ids = {x["txid"] for x in accepted}
    c["mempool"] = [x for x in c["mempool"] if x["txid"] not in accepted_ids]
    ok, reason = validate_chain(c)
    if not ok: raise RuntimeError(f"Internal validation failed: {reason}")
    save_chain(c)
    return b


def cli() -> int:
    p = argparse.ArgumentParser(description="TKC educational testnet node")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wallet-new"); w.add_argument("name")
    b = sub.add_parser("balance"); b.add_argument("wallet")
    s = sub.add_parser("send"); s.add_argument("wallet"); s.add_argument("to"); s.add_argument("amount", type=int); s.add_argument("--fee", type=int, default=0)
    m = sub.add_parser("mine"); m.add_argument("wallet")
    sub.add_parser("status"); sub.add_parser("verify"); sub.add_parser("blocks")
    a = p.parse_args()
    try:
        if a.cmd == "wallet-new":
            path = create_wallet(a.name); d = json.loads(path.read_text()); print(f"Wallet: {path}\nAddress: {d['address']}\nKeep the private key file secret; this is testnet only."); return 0
        c = load_chain()
        if a.cmd == "verify":
            ok, msg = validate_chain(c); print(("PASS: " if ok else "FAIL: ") + msg); return 0 if ok else 1
        if a.cmd == "status":
            _, _, minted = chain_state(c["blocks"]); print(f"Network: {NETWORK}\nVersion: {VERSION}\nHeight: {len(c['blocks'])-1}\nPending transactions: {len(c['mempool'])}\nMining rewards issued: {minted:,}/{MINING_ALLOCATION:,} TKC\nPlanned max supply: {MAX_SUPPLY:,} TKC (not fully implemented)\nDifficulty: {DIFFICULTY} leading zeroes\n{validate_chain(c)[1]}"); return 0
        if a.cmd == "blocks":
            for x in c["blocks"][-10:]: print(f"#{x['height']} {x['hash']} miner={x['miner']} txs={len(x['transactions'])}")
            return 0
        wallet = load_wallet(a.wallet)
        balances, _, _ = chain_state(c["blocks"])
        if a.cmd == "balance": print(f"{wallet['address']}\nBalance: {balances.get(wallet['address'], 0)} TKC (testnet)"); return 0
        if a.cmd == "send":
            tx = make_transaction(wallet, a.to, a.amount, a.fee, current_nonce(c, wallet["address"])+1); submit_tx(c, tx); print(f"Queued transaction: {tx['txid']}"); return 0
        if a.cmd == "mine":
            block = mine(c, wallet["address"]); print(f"Mined block #{block['height']}\nHash: {block['hash']}\nReward: {BLOCK_REWARD} TKC testnet"); return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); return 1
    return 0

if __name__ == "__main__": raise SystemExit(cli())
