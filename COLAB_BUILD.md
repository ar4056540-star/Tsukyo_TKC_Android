# TKC Android Colab build project v0.2

This project wraps the uploaded `Tsukyo_TKC_Educational_Testnet_v0.2.zip` source in a basic Kivy Android UI. It is an educational single-device testnet, not a production wallet or decentralized network.

## Colab
Upload this ZIP using:
```python
from google.colab import files
uploaded = files.upload()
```
Then run:
```bash
!apt-get update -y
!apt-get install -y git zip unzip openjdk-17-jdk python3-pip build-essential autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
!pip install --upgrade pip setuptools wheel
!pip install buildozer cython==0.29.36
!unzip -q TKC_Android_Colab_Project_v0.2.zip -d /content/tkcbuild
%cd /content/tkcbuild
!buildozer -v android debug
```
Download APK:
```python
from google.colab import files
import glob
apks = glob.glob('/content/tkcbuild/bin/*.apk')
print(apks)
assert apks, "Build did not produce an APK. Inspect the build log above."
files.download(apks[0])
```

## Important build note
The `cryptography` package uses native components. Buildozer/python-for-android compatibility can vary by toolchain version. This configuration is a build attempt, not a verified APK. If the build fails at `cryptography`, share the first actual error lines; do not replace the blockchain's signature verification with a fake implementation.
