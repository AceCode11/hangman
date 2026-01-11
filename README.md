These game was completely build using AI tools because of my College mini prj which help to understand the md5 comcepts and secure terminal so I used AI to build these projectl.Thank you





# 🎮 Realistic Multiplayer Hangman (Secure Edition)

A high-fidelity two-player Hangman game demonstrating **secure communication** and **physics-based animation**.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Pygame](https://img.shields.io/badge/GUI-Pygame-red)
![Encryption](https://img.shields.io/badge/Security-AES--128%20%2B%20MD5-orange)

## 🚀 How to Play

### 1. Realistic Version (Recommended)
Features a **physics-based ragdoll** stickman that reacts to gravity, a sleek dark UI, and dramatic death animations.
```bash
python pygame_hangman.py
```

### 2. Standard Version (Simple)
A lightweight version using standard window controls.
```bash
python hangman.py
```

---

## 🔐 Security Features
Both versions run as a single application that simulates a secure network tunnel between two players:

1.  **Secure Tunnel**: The "server" (internal logic) simulates a relay that never sees the plaintext word.
2.  **Fernet Encryption**: The secret word is encrypted (AES-128) immediately upon entry.
3.  **MD5 Integrity**: An MD5 hash is generated to detect any tampering during "transmission".
4.  **Simulated Attacks**: There is a **20% chance** that an "attacker" will intercept and modify the encrypted data, triggering an **INTEGRITY BREACH** warning to demonstrate how hashing protects data.

## 🎮 Game Flow
1.  **Player 1** enters a secret word (hidden).
2.  Word is **Encrypted** and "Sent".
3.  **Player 2** takes over (Player 1 looks away).
4.  **Integrity Check** runs automatically.
5.  **Player 2** guesses letters using the keyboard.
6.  **Win if** you guess the word. **Lose if** the stickman fully collapses in regret.

## 📂 Project Structure
*   `pygame_hangman.py` - Main high-fidelity game (Pygame)
*   `hangman.py` - Alternative standard version (Tkinter)
*   `README.md` - Instructions

## 📝 License
MIT License - Educational Use Only
