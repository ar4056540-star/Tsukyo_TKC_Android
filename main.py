import os, sys, traceback
from pathlib import Path

# Keep blockchain data in Android app's private writable storage.
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("ANDROID_PRIVATE", str(APP_DIR))) / "tkc_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(APP_DIR / "tkc_core"))
import tkc
tkc.ROOT = DATA_DIR
tkc.DATA = DATA_DIR / "data"
tkc.CHAIN_FILE = tkc.DATA / "chain.json"
tkc.WALLETS = DATA_DIR / "wallets"

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

class TKCApp(App):
    def build(self):
        self.title = "Tsukyo Coin Testnet"
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(Label(text="[b]TSUKYO COIN[/b]  |  EDUCATIONAL TESTNET", markup=True,
                              size_hint_y=None, height=42, color=(1,.2,.25,1)))
        self.name = TextInput(hint_text="Wallet name (e.g. aryan)", multiline=False, size_hint_y=None, height=46)
        root.add_widget(self.name)
        self.output = Label(text="Create a testnet wallet, then mine a block.", size_hint_y=None,
                            halign="left", valign="top", markup=True)
        self.output.bind(width=lambda *_: setattr(self.output, "text_size", (self.output.width, None)))
        scroll = ScrollView()
        scroll.add_widget(self.output)
        root.add_widget(scroll)
        for label, fn in [
            ("Create wallet", self.create_wallet),
            ("Start mining (1 TKC reward)", self.mine),
            ("Check balance", self.balance),
            ("Blockchain status", self.status),
            ("Verify blockchain", self.verify),
        ]:
            btn = Button(text=label, size_hint_y=None, height=48)
            btn.bind(on_release=lambda _b, f=fn: f())
            root.add_widget(btn)
        root.add_widget(Label(text="TESTNET ONLY • NO MONETARY VALUE", size_hint_y=None, height=28))
        return root

    def wallet_name(self):
        n = self.name.text.strip()
        if not n: raise ValueError("Enter a wallet name first.")
        return n

    def show(self, msg):
        self.output.text = str(msg)

    def create_wallet(self):
        try:
            p = tkc.create_wallet(self.wallet_name())
            import json
            w = json.loads(p.read_text())
            self.show("Wallet created\n\nName: %s\nAddress: %s\n\nWallet file saved in app-private storage. Back it up securely; never share private keys." % (w["name"], w["address"]))
        except Exception as e: self.show("Error: " + str(e))

    def get_wallet(self):
        return tkc.load_wallet(self.wallet_name())

    def mine(self):
        try:
            w = self.get_wallet()
            c = tkc.load_chain()
            b = tkc.mine(c, w["address"])
            self.show("Mining successful!\n\nBlock: %s\nReward: 1 TKC\nHash: %s" % (b["height"], b["hash"]))
        except Exception as e: self.show("Mining error: " + str(e))

    def balance(self):
        try:
            w = self.get_wallet()
            c = tkc.load_chain()
            balances, _, _ = tkc.chain_state(c["blocks"])
            self.show("Wallet: %s\nAddress: %s\nBalance: %s TKC" % (w["name"], w["address"], balances.get(w["address"], 0)))
        except Exception as e: self.show("Error: " + str(e))

    def status(self):
        try:
            c = tkc.load_chain()
            _, _, minted = tkc.chain_state(c["blocks"])
            self.show("Network: %s\nVersion: %s\nBlock height: %s\nPending transactions: %s\nMining issued: %s / %s TKC" %
                      (tkc.NETWORK, tkc.VERSION, len(c["blocks"])-1, len(c["mempool"]), minted, tkc.MINING_ALLOCATION))
        except Exception as e: self.show("Error: " + str(e))

    def verify(self):
        try:
            c = tkc.load_chain()
            ok, msg = tkc.validate_chain(c)
            self.show(("PASS: " if ok else "FAIL: ") + msg)
        except Exception as e: self.show("Error: " + str(e))

if __name__ == "__main__":
    TKCApp().run()
