# FengAK
**FengAK** is a lightweight, command-line based network stress testing tool written in Python. It is designed for educational purposes and network security testing.
> **⚠️ IMPORTANT LEGAL DISCLAIMER**
>
> **FengAK** is intended for **educational and authorized security testing purposes only**.
>
> - **Do not** use this tool to attack networks or servers without explicit permission from the owner.
> - **Do not** use this tool for any illegal activities.
> - The author (FengPwner) is **not responsible** for any damage or legal consequences caused by the misuse of this software.
> - **You are solely responsible for your actions.** By using this tool, you agree to comply with all applicable local, state, and federal laws.
---
### Features
- **UDP Flood:** Capable of sending high-volume UDP packets to stress test target availability.
- **Lightweight:** Written in pure Python using standard libraries (`socket`, `random`, `threading`).
- **Cross-Platform:** Runs on any system with Python 3 installed (Linux, macOS, Windows, Termux).
- **Visual Banner:** Includes a stylized ASCII art banner for a classic CLI look.
- **Real-time Stats:** Displays attack duration and status in the terminal.
---
### Installation
1. **Clone the repository:**
```bash
git clone https://github.com/FengPwner/FengPYkit.git
cd FengPYkit
```
2. **Ensure you have Python 3 installed:**
```bash
   python3 --version
```
3.(Optional) Install `figlet` for the best visual experience:
If `figlet` is not installed, the script will fallback to a standard text banner.

◦Debian/Ubuntu/Kali: `sudo apt install figlet`

◦Termux: `pkg install figlet`

◦MacOS: `brew install figlet`

## Use
**Run the script using Python 3:**
```
python3 FengAK.py
```

## License

This project is open-source. Please use responsibly.

Author: FengPwner

Version: S1.3