# Hangman - Single Application Version
# Run this file to play the complete game in one window

import tkinter as tk
from tkinter import messagebox
import threading
import hashlib
import base64
import random
import time

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Installing cryptography package...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography", "-q"])
    from cryptography.fernet import Fernet

# ============== CONFIGURATION ==============
COLORS = {
    'bg_dark': '#1a1a2e',
    'bg_medium': '#16213e',
    'bg_light': '#0f3460',
    'accent': '#e94560',
    'success': '#00d9a5',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'text_light': '#ffffff',
    'text_muted': '#8892b0',
    'gallows': '#4a5568',
    'body': '#ffd93d'
}

MAX_WRONG_GUESSES = 6
ATTACK_PROBABILITY = 0.2  # 20% chance of simulated attack

# ============== CRYPTO UTILITIES ==============
class CryptoManager:
    def __init__(self, key=None):
        if key is None:
            self.key = Fernet.generate_key()
        else:
            self.key = self._ensure_valid_key(key)
        self.cipher = Fernet(self.key)
    
    def _ensure_valid_key(self, key):
        try:
            Fernet(key)
            return key
        except:
            hash_bytes = hashlib.sha256(key).digest()
            return base64.urlsafe_b64encode(hash_bytes)
    
    def encrypt(self, plaintext):
        return self.cipher.encrypt(plaintext.encode('utf-8'))
    
    def decrypt(self, ciphertext):
        return self.cipher.decrypt(ciphertext).decode('utf-8')
    
    @staticmethod
    def generate_md5(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_integrity(text, expected_hash):
        return CryptoManager.generate_md5(text) == expected_hash
    
    def get_key(self):
        return self.key


# ============== HANGMAN GRAPHICS ==============
class HangmanCanvas:
    def __init__(self, parent, width=280, height=280):
        self.canvas = tk.Canvas(
            parent, width=width, height=height,
            bg=COLORS['bg_dark'], highlightthickness=0
        )
        self.wrong_guesses = 0
        self._draw_gallows()
    
    def _draw_gallows(self):
        c = self.canvas
        c.create_line(20, 260, 160, 260, fill=COLORS['gallows'], width=4)
        c.create_line(50, 260, 50, 30, fill=COLORS['gallows'], width=4)
        c.create_line(50, 30, 150, 30, fill=COLORS['gallows'], width=4)
        c.create_line(150, 30, 150, 55, fill=COLORS['gallows'], width=3)
        c.create_line(50, 70, 90, 30, fill=COLORS['gallows'], width=3)
    
    def add_wrong_guess(self):
        self.wrong_guesses += 1
        c = self.canvas
        body_color = COLORS['body']
        
        if self.wrong_guesses == 1:  # Head
            c.create_oval(130, 55, 170, 95, outline=body_color, width=3, tags='body')
        elif self.wrong_guesses == 2:  # Body
            c.create_line(150, 95, 150, 170, fill=body_color, width=3, tags='body')
        elif self.wrong_guesses == 3:  # Left arm
            c.create_line(150, 115, 115, 145, fill=body_color, width=3, tags='body')
        elif self.wrong_guesses == 4:  # Right arm
            c.create_line(150, 115, 185, 145, fill=body_color, width=3, tags='body')
        elif self.wrong_guesses == 5:  # Left leg
            c.create_line(150, 170, 115, 220, fill=body_color, width=3, tags='body')
        elif self.wrong_guesses == 6:  # Right leg
            c.create_line(150, 170, 185, 220, fill=body_color, width=3, tags='body')
    
    def reset(self):
        self.wrong_guesses = 0
        self.canvas.delete('body')
    
    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)


# ============== MAIN GAME APPLICATION ==============
class HangmanGame:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hangman - Secure Communication Demo")
        self.root.geometry("800x650")
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.resizable(True, True)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 800) // 2
        y = (self.root.winfo_screenheight() - 650) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Game state
        self.secret_word = ""
        self.encrypted_word = None
        self.md5_hash = ""
        self.guessed_letters = set()
        self.wrong_guesses = 0
        self.revealed = []
        self.game_active = False
        self.attack_occurred = False
        self.crypto = None
        
        self._create_ui()
    
    def _create_ui(self):
        # Main container
        main = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main.pack(expand=True, fill='both', padx=20, pady=15)
        
        # Title
        tk.Label(
            main, text="HANGMAN - Secure Communication Demo",
            font=('Segoe UI', 18, 'bold'),
            fg=COLORS['accent'], bg=COLORS['bg_dark']
        ).pack(pady=(0, 10))
        
        # Content frame (two columns)
        content = tk.Frame(main, bg=COLORS['bg_dark'])
        content.pack(expand=True, fill='both')
        
        # Left column - Hangman + Word
        left = tk.Frame(content, bg=COLORS['bg_dark'])
        left.pack(side='left', fill='both', expand=True, padx=10)
        
        # Hangman canvas
        self.hangman = HangmanCanvas(left)
        self.hangman.pack(pady=10)
        
        # Word display
        self.word_label = tk.Label(
            left, text="_ _ _ _ _",
            font=('Consolas', 28, 'bold'),
            fg=COLORS['text_light'], bg=COLORS['bg_dark']
        )
        self.word_label.pack(pady=15)
        
        # Message
        self.message_label = tk.Label(
            left, text="Enter a word to start",
            font=('Segoe UI', 12),
            fg=COLORS['text_muted'], bg=COLORS['bg_dark']
        )
        self.message_label.pack(pady=5)
        
        # Right column - Controls + Status
        right = tk.Frame(content, bg=COLORS['bg_medium'], padx=15, pady=15)
        right.pack(side='right', fill='y', padx=10)
        
        # Word entry section
        tk.Label(
            right, text="PLAYER 1: Set Word",
            font=('Segoe UI', 12, 'bold'),
            fg=COLORS['accent'], bg=COLORS['bg_medium']
        ).pack(anchor='w', pady=(0, 5))
        
        # Masked entry (like password field)
        self.word_entry = tk.Entry(
            right, font=('Segoe UI', 14), width=15,
            fg=COLORS['text_light'], bg=COLORS['bg_dark'],
            insertbackground=COLORS['text_light'], relief='flat',
            show='●'  # Hide the letters!
        )
        self.word_entry.pack(fill='x', pady=5, ipady=8)
        self.word_entry.bind('<Return>', lambda e: self._set_word())
        
        # Show/hide toggle
        self.show_word_var = tk.BooleanVar(value=False)
        self.show_word_check = tk.Checkbutton(
            right, text="Show letters (Player 1 only)",
            font=('Segoe UI', 9),
            fg=COLORS['text_muted'], bg=COLORS['bg_medium'],
            selectcolor=COLORS['bg_dark'],
            activebackground=COLORS['bg_medium'],
            variable=self.show_word_var,
            command=self._toggle_word_visibility
        )
        self.show_word_check.pack(anchor='w')
        
        self.set_word_btn = tk.Button(
            right, text="ENCRYPT & SET WORD",
            font=('Segoe UI', 11, 'bold'),
            fg='white', bg=COLORS['accent'],
            relief='flat', cursor='hand2',
            command=self._set_word
        )
        self.set_word_btn.pack(fill='x', pady=5, ipady=5)
        
        # Separator
        tk.Frame(right, height=2, bg=COLORS['bg_light']).pack(fill='x', pady=15)
        
        # Status section
        tk.Label(
            right, text="SECURITY STATUS",
            font=('Segoe UI', 11, 'bold'),
            fg=COLORS['text_light'], bg=COLORS['bg_medium']
        ).pack(anchor='w', pady=(0, 5))
        
        # Status labels
        self.session_status = tk.Label(
            right, text="● Session: Not started",
            font=('Segoe UI', 10), anchor='w',
            fg=COLORS['text_muted'], bg=COLORS['bg_medium']
        )
        self.session_status.pack(anchor='w', pady=2)
        
        self.encryption_status = tk.Label(
            right, text="● Encryption: Pending",
            font=('Segoe UI', 10), anchor='w',
            fg=COLORS['text_muted'], bg=COLORS['bg_medium']
        )
        self.encryption_status.pack(anchor='w', pady=2)
        
        self.integrity_status = tk.Label(
            right, text="● Integrity: Pending",
            font=('Segoe UI', 10), anchor='w',
            fg=COLORS['text_muted'], bg=COLORS['bg_medium']
        )
        self.integrity_status.pack(anchor='w', pady=2)
        
        self.attack_status = tk.Label(
            right, text="● Attack: None",
            font=('Segoe UI', 10), anchor='w',
            fg=COLORS['text_muted'], bg=COLORS['bg_medium']
        )
        self.attack_status.pack(anchor='w', pady=2)
        
        self.attempts_label = tk.Label(
            right, text=f"● Attempts: {MAX_WRONG_GUESSES} left",
            font=('Segoe UI', 10), anchor='w',
            fg=COLORS['success'], bg=COLORS['bg_medium']
        )
        self.attempts_label.pack(anchor='w', pady=2)
        
        # Separator
        tk.Frame(right, height=2, bg=COLORS['bg_light']).pack(fill='x', pady=15)
        
        # Keyboard section
        tk.Label(
            right, text="PLAYER 2: Guess Letters",
            font=('Segoe UI', 12, 'bold'),
            fg=COLORS['accent'], bg=COLORS['bg_medium']
        ).pack(anchor='w', pady=(0, 10))
        
        self.keyboard_frame = tk.Frame(right, bg=COLORS['bg_medium'])
        self.keyboard_frame.pack()
        self._create_keyboard()
        
        # New game button
        tk.Frame(right, height=2, bg=COLORS['bg_light']).pack(fill='x', pady=15)
        
        self.new_game_btn = tk.Button(
            right, text="NEW GAME",
            font=('Segoe UI', 11, 'bold'),
            fg='white', bg=COLORS['bg_light'],
            relief='flat', cursor='hand2',
            command=self._new_game
        )
        self.new_game_btn.pack(fill='x', ipady=5)
    
    def _create_keyboard(self):
        self.letter_buttons = {}
        rows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
        
        for row_letters in rows:
            row = tk.Frame(self.keyboard_frame, bg=COLORS['bg_medium'])
            row.pack(pady=2)
            
            for letter in row_letters:
                btn = tk.Button(
                    row, text=letter,
                    font=('Segoe UI', 10, 'bold'),
                    width=2, height=1,
                    fg=COLORS['text_light'], bg=COLORS['bg_dark'],
                    relief='flat', cursor='hand2',
                    state='disabled',
                    command=lambda l=letter: self._guess_letter(l)
                )
                btn.pack(side='left', padx=1)
                self.letter_buttons[letter] = btn
    
    def _toggle_word_visibility(self):
        """Toggle showing/hiding the word entry."""
        if self.show_word_var.get():
            self.word_entry.config(show='')  # Show letters
        else:
            self.word_entry.config(show='●')  # Hide letters
    
    def _set_word(self):
        word = self.word_entry.get().strip().upper()
        
        if not word:
            messagebox.showerror("Error", "Please enter a word!")
            return
        
        if not word.isalpha():
            messagebox.showerror("Error", "Word must contain only letters!")
            return
        
        if len(word) < 2:
            messagebox.showerror("Error", "Word must be at least 2 letters!")
            return
        
        # Clear the entry immediately so Player 2 can't see it
        self.word_entry.delete(0, 'end')
        self.word_entry.config(state='disabled')
        self.set_word_btn.config(state='disabled')
        self.show_word_check.config(state='disabled')
        
        # Start secure session
        self.secret_word = word
        self.crypto = CryptoManager()
        
        # Update status - Session
        self.session_status.config(
            text="● Session: Secure tunnel active",
            fg=COLORS['success']
        )
        
        # Encrypt the word
        self.encrypted_word = self.crypto.encrypt(word)
        self.md5_hash = self.crypto.generate_md5(word)
        
        self.encryption_status.config(
            text="● Encryption: AES-128 applied",
            fg=COLORS['success']
        )
        
        # Show Player 2 transition
        self._show_player2_transition()
    
    def _show_player2_transition(self):
        """Show a fullscreen overlay for Player 2 to take over."""
        # Create overlay
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("Player 2's Turn")
        self.overlay.geometry("500x350")
        self.overlay.configure(bg=COLORS['bg_dark'])
        self.overlay.resizable(False, False)
        self.overlay.transient(self.root)
        self.overlay.grab_set()  # Modal
        
        # Center
        self.overlay.update_idletasks()
        x = (self.overlay.winfo_screenwidth() - 500) // 2
        y = (self.overlay.winfo_screenheight() - 350) // 2
        self.overlay.geometry(f"+{x}+{y}")
        
        tk.Label(
            self.overlay,
            text="🔐 WORD ENCRYPTED!",
            font=('Segoe UI', 24, 'bold'),
            fg=COLORS['success'], bg=COLORS['bg_dark']
        ).pack(pady=(40, 10))
        
        tk.Label(
            self.overlay,
            text="Player 1: Look away now!",
            font=('Segoe UI', 16),
            fg=COLORS['warning'], bg=COLORS['bg_dark']
        ).pack(pady=5)
        
        tk.Label(
            self.overlay,
            text="Player 2: Click the button when ready to guess.",
            font=('Segoe UI', 14),
            fg=COLORS['text_light'], bg=COLORS['bg_dark']
        ).pack(pady=15)
        
        tk.Label(
            self.overlay,
            text=f"Word length: {len(self.secret_word)} letters",
            font=('Segoe UI', 12),
            fg=COLORS['text_muted'], bg=COLORS['bg_dark']
        ).pack(pady=5)
        
        tk.Button(
            self.overlay,
            text="I'M PLAYER 2 - START GUESSING!",
            font=('Segoe UI', 14, 'bold'),
            fg='white', bg=COLORS['accent'],
            relief='flat', cursor='hand2',
            padx=30, pady=15,
            command=self._player2_ready
        ).pack(pady=30)
    
    def _player2_ready(self):
        """Player 2 clicked ready - close overlay and simulate transmission."""
        self.overlay.destroy()
        self._simulate_transmission()
    
    def _simulate_transmission(self):
        self.message_label.config(text="Transmitting encrypted data...", fg=COLORS['warning'])
        self.root.update()
        
        # Simulate network delay
        self.root.after(500, self._check_for_attack)
    
    def _check_for_attack(self):
        # Simulate attacker with configurable probability
        if random.random() < ATTACK_PROBABILITY:
            self.attack_occurred = True
            self.attack_status.config(
                text="● Attack: DATA MODIFIED!",
                fg=COLORS['danger']
            )
            
            # Modify encrypted data
            modified = list(self.encrypted_word)
            if len(modified) > 20:
                modified[15] = modified[15] ^ 0xFF  # Flip bits
            self.encrypted_word = bytes(modified)
            
            self.message_label.config(
                text="⚠️ ATTACKER INTERCEPTED DATA!",
                fg=COLORS['danger']
            )
        else:
            self.attack_status.config(
                text="● Attack: None detected",
                fg=COLORS['success']
            )
        
        self.root.after(800, self._verify_integrity)
    
    def _verify_integrity(self):
        self.message_label.config(text="Verifying integrity with MD5...", fg=COLORS['warning'])
        self.root.update()
        
        try:
            # Decrypt
            decrypted = self.crypto.decrypt(self.encrypted_word)
            
            # Verify MD5
            if self.crypto.verify_integrity(decrypted, self.md5_hash):
                self.integrity_status.config(
                    text="● Integrity: VERIFIED ✓",
                    fg=COLORS['success']
                )
                self.root.after(500, self._start_game)
            else:
                self._integrity_failed()
        except Exception:
            self._integrity_failed()
    
    def _integrity_failed(self):
        self.integrity_status.config(
            text="● Integrity: FAILED ✗",
            fg=COLORS['danger']
        )
        self.message_label.config(
            text="⚠️ INTEGRITY BREACH! Data was tampered!",
            fg=COLORS['danger']
        )
        self.word_label.config(text="TAMPERED!", fg=COLORS['danger'])
        
        # Disable game
        self.set_word_btn.config(state='disabled')
        for btn in self.letter_buttons.values():
            btn.config(state='disabled')
    
    def _start_game(self):
        self.game_active = True
        self.revealed = ['_'] * len(self.secret_word)
        self._update_word_display()
        
        self.message_label.config(
            text="Game started! Guess the word.",
            fg=COLORS['success']
        )
        
        # Disable word entry, enable keyboard
        self.word_entry.config(state='disabled')
        self.set_word_btn.config(state='disabled')
        
        for btn in self.letter_buttons.values():
            btn.config(state='normal')
    
    def _guess_letter(self, letter):
        if not self.game_active or letter in self.guessed_letters:
            return
        
        self.guessed_letters.add(letter)
        self.letter_buttons[letter].config(state='disabled')
        
        if letter in self.secret_word:
            # Correct guess
            for i, c in enumerate(self.secret_word):
                if c == letter:
                    self.revealed[i] = letter
            
            self._update_word_display()
            self.letter_buttons[letter].config(bg=COLORS['success'])
            self.message_label.config(text="Correct! ✓", fg=COLORS['success'])
            
            # Check win
            if '_' not in self.revealed:
                self._game_won()
        else:
            # Wrong guess
            self.wrong_guesses += 1
            self.hangman.add_wrong_guess()
            self.letter_buttons[letter].config(bg=COLORS['danger'])
            
            remaining = MAX_WRONG_GUESSES - self.wrong_guesses
            color = COLORS['success'] if remaining > 2 else (COLORS['warning'] if remaining > 1 else COLORS['danger'])
            self.attempts_label.config(text=f"● Attempts: {remaining} left", fg=color)
            self.message_label.config(text="Wrong! ✗", fg=COLORS['danger'])
            
            # Check lose
            if self.wrong_guesses >= MAX_WRONG_GUESSES:
                self._game_lost()
    
    def _update_word_display(self):
        self.word_label.config(text=' '.join(self.revealed), fg=COLORS['text_light'])
    
    def _game_won(self):
        self.game_active = False
        self.word_label.config(fg=COLORS['success'])
        self.message_label.config(text="🎉 YOU WIN!", fg=COLORS['success'])
        
        for btn in self.letter_buttons.values():
            btn.config(state='disabled')
    
    def _game_lost(self):
        self.game_active = False
        self.revealed = list(self.secret_word)
        self._update_word_display()
        self.word_label.config(fg=COLORS['danger'])
        self.message_label.config(
            text=f"💀 GAME OVER! Word was: {self.secret_word}",
            fg=COLORS['danger']
        )
        
        for btn in self.letter_buttons.values():
            btn.config(state='disabled')
    
    def _new_game(self):
        # Reset all state
        self.secret_word = ""
        self.encrypted_word = None
        self.md5_hash = ""
        self.guessed_letters = set()
        self.wrong_guesses = 0
        self.revealed = []
        self.game_active = False
        self.attack_occurred = False
        self.crypto = None
        
        # Reset UI
        self.hangman.reset()
        self.word_label.config(text="_ _ _ _ _", fg=COLORS['text_light'])
        self.message_label.config(text="Enter a word to start", fg=COLORS['text_muted'])
        
        self.word_entry.config(state='normal', show='●')
        self.word_entry.delete(0, 'end')
        self.set_word_btn.config(state='normal')
        self.show_word_var.set(False)
        self.show_word_check.config(state='normal')
        
        # Reset status
        self.session_status.config(text="● Session: Not started", fg=COLORS['text_muted'])
        self.encryption_status.config(text="● Encryption: Pending", fg=COLORS['text_muted'])
        self.integrity_status.config(text="● Integrity: Pending", fg=COLORS['text_muted'])
        self.attack_status.config(text="● Attack: None", fg=COLORS['text_muted'])
        self.attempts_label.config(text=f"● Attempts: {MAX_WRONG_GUESSES} left", fg=COLORS['success'])
        
        # Reset keyboard
        for letter, btn in self.letter_buttons.items():
            btn.config(state='disabled', bg=COLORS['bg_dark'])
    
    def run(self):
        self.root.mainloop()


# ============== MAIN ==============
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  HANGMAN - Secure Communication Demo")
    print("=" * 50)
    print("\nStarting game...")
    
    game = HangmanGame()
    game.run()
