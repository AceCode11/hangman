import pygame
import math
import sys
import random
import hashlib
import base64
import time

try:
    from cryptography.fernet import Fernet
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography.fernet import Fernet

# Initialize Pygame
pygame.init()

# ================= CONFIGURATION =================
WIDTH, HEIGHT = 1000, 700
FPS = 60
TITLE = "Hangman"

# Dark Atmospheric Palette
DARK_BG = (8, 8, 12)           # Near black with hint of blue
PANEL_BG = (15, 15, 20)        # Slightly lighter
GALLOWS_COLOR = (35, 30, 28)   # Dark wood brown
ACCENT = (140, 25, 25)         # Dark blood red
ACCENT_BRIGHT = (180, 40, 40)  # Brighter red for hover
SUCCESS = (30, 120, 60)        # Muted green
TEXT_WHITE = (200, 200, 200)   # Off-white
TEXT_GRAY = (80, 80, 90)       # Dim gray
TEXT_DIM = (50, 50, 55)        # Very dim
ROPE_COLOR = (90, 70, 50)      # Dark hemp
STICKMAN_COLOR = (180, 175, 170) # Pale gray/bone color

# Fonts
FONT_TITLE = pygame.font.SysFont('segoeui', 56, bold=True)
FONT_HEADING = pygame.font.SysFont('segoeui', 36)
FONT_BODY = pygame.font.SysFont('segoeui', 26)
FONT_SMALL = pygame.font.SysFont('consolas', 18)
FONT_WORD = pygame.font.SysFont('consolas', 60, bold=True)         

# Physics Constants
GRAVITY = 0.6
DAMPING = 0.92  # slightly less damping for more swing

# ================= CRYPTO UTILITIES =================
class CryptoManager:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
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

# ================= PHYSICS CLASSES =================
class Point:
    def __init__(self, x, y, locked=False):
        self.x, self.y = x, y
        self.old_x, self.old_y = x, y
        self.locked = locked

class Stick:
    def __init__(self, p1, p2, length=None):
        self.p1, self.p2 = p1, p2
        if length is None:
            self.length = math.hypot(p2.x - p1.x, p2.y - p1.y)
        else:
            self.length = length

class BloodParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-1, 3)
        self.size = random.uniform(2, 5)
        self.color = (random.randint(180, 255), 0, 0) # Varied blood red
        self.life = 255
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # Gravity
        self.life -= 4
        if self.y > 600: # Floor splatter
            self.y = 600
            self.vx *= 0.5
            self.vy = 0

    def draw(self, screen):
        if self.life > 0:
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, int(self.life)), (int(self.size), int(self.size)), int(self.size))
            screen.blit(s, (int(self.x-self.size), int(self.y-self.size)))

# ================= UI COMPONENTS =================
class Button:
    def __init__(self, x, y, w, h, text, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.is_hovered = False

    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, (10, 10, 10), self.rect.move(3, 3), border_radius=10)
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        txt_surf = FONT_BODY.render(self.text, True, TEXT_WHITE)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)

    def click(self):
        if self.action:
            self.action()

class InputBox:
    def __init__(self, x, y, w, h, font, is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = TEXT_GRAY
        self.color_active = ACCENT
        self.color = self.color_inactive
        self.text = ''
        self.font = font
        self.active = True
        self.is_password = is_password

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isalpha() and len(self.text) < 20:
                self.text += event.unicode.upper()
        return None

    def draw(self, screen):
        display_text = '●' * len(self.text) if self.is_password else self.text
        txt_surface = self.font.render(display_text, True, TEXT_WHITE)
        pygame.draw.rect(screen, PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=8)
        screen.blit(txt_surface, (self.rect.x + 15, self.rect.y + 10))

# ================= PHYSICS SIMULATION =================
class Ragdoll:
    def __init__(self, x, y):
        self.points = []
        self.sticks = []
        self.wrong_count = 0
        
        # Origin (Gallows anchor)
        self.anchor = Point(x, y, locked=True)
        self.points.append(self.anchor)
        
        # Head (Pivot)
        head_x, head_y = x, y + 40
        self.head = Point(head_x, head_y) # 1
        self.points.append(self.head)
        self.rope = Stick(self.anchor, self.head, length=40)
        self.sticks.append(self.rope)
        
        # Neck
        neck = Point(head_x, head_y + 25) # 2
        self.points.append(neck)
        self.sticks.append(Stick(self.head, neck)) # Head-Neck
        
        # Pelvis
        pelvis = Point(head_x, head_y + 90) # 3
        self.points.append(pelvis)
        self.torso_stick = Stick(neck, pelvis)
        self.sticks.append(self.torso_stick)
        
        # Arms
        l_elbow = Point(head_x - 30, head_y + 40) # 4
        l_hand = Point(head_x - 50, head_y + 60)  # 5
        self.points.extend([l_elbow, l_hand])
        self.l_arm_sticks = [Stick(neck, l_elbow), Stick(l_elbow, l_hand)]
        self.sticks.extend(self.l_arm_sticks)

        r_elbow = Point(head_x + 30, head_y + 40) # 6
        r_hand = Point(head_x + 50, head_y + 60)  # 7
        self.points.extend([r_elbow, r_hand])
        self.r_arm_sticks = [Stick(neck, r_elbow), Stick(r_elbow, r_hand)]
        self.sticks.extend(self.r_arm_sticks)
        
        # Legs
        l_knee = Point(head_x - 15, head_y + 130) # 8
        l_foot = Point(head_x - 15, head_y + 170) # 9
        self.points.extend([l_knee, l_foot])
        self.l_leg_sticks = [Stick(pelvis, l_knee), Stick(l_knee, l_foot)]
        self.sticks.extend(self.l_leg_sticks)

        r_knee = Point(head_x + 15, head_y + 130) # 10
        r_foot = Point(head_x + 15, head_y + 170) # 11
        self.points.extend([r_knee, r_foot])
        self.r_leg_sticks = [Stick(pelvis, r_knee), Stick(r_knee, r_foot)]
        self.sticks.extend(self.r_leg_sticks)
        
        self.sway_timer = 0
        self.death_timer = 0
        
        # Pop/Growth Animation Progress (0.0 to 1.0) for each stage (0-6)
        self.pop_progress = [0.0] * 7
        self.prev_wrong_count = 0
        
        self.blood_particles = []
        self.rope_snapped = False

    def update(self):
        # Update Pop Animations
        for i in range(len(self.pop_progress)):
            if i <= self.wrong_count and self.pop_progress[i] < 1.0:
                self.pop_progress[i] += 0.1 # Fast pop
                if self.pop_progress[i] > 1.0: self.pop_progress[i] = 1.0
                
        # Update Blood
        for b in self.blood_particles[:]:
            b.update()
            if b.life <= 0:
                self.blood_particles.remove(b)
                
        # Physics (Verlet)
        for p in self.points:
            if not p.locked:
                vx = (p.x - p.old_x) * DAMPING
                vy = (p.y - p.old_y) * DAMPING
                p.old_x, p.old_y = p.x, p.y
                p.x += vx
                p.y += vy
                p.y += GRAVITY
                
                # Floor collision if rope snapped
                if self.rope_snapped and p.y > 600:
                   p.y = 600
                   p.x -= vx * 0.5 # Friction

        # Constraints
        for _ in range(5):
            for s in self.sticks:
                # If part is not fully grown, maybe we should constrain it tightly to start? 
                # No, let physics run, we just draw it growing.
                dx = s.p2.x - s.p1.x
                dy = s.p2.y - s.p1.y
                dist = math.hypot(dx, dy)
                if dist == 0: continue
                diff = (s.length - dist) / dist * 0.5
                offset_x, offset_y = dx * diff, dy * diff
                if not s.p1.locked:
                    s.p1.x -= offset_x
                    s.p1.y -= offset_y
                if not s.p2.locked:
                    s.p2.x += offset_x
                    s.p2.y += offset_y
                    
        # Death Animation Logic
        if self.wrong_count >= 6 and self.pop_progress[6] >= 1.0:
            self.death_timer += 1
            
            # Phase 1: STRUGGLE & BLEED (~2 sec)
            if self.death_timer < 120:
                # Add blood spurts from neck
                if random.random() < 0.3:
                    self.blood_particles.append(BloodParticle(self.points[2].x, self.points[2].y)) # Neck
                
                # Hands reach up toward rope desperately
                target_y = self.head.y - 10
                self.points[5].y += (target_y - self.points[5].y) * 0.05
                self.points[7].y += (target_y - self.points[7].y) * 0.05
                self.points[5].x += (self.head.x - 20 - self.points[5].x) * 0.03
                self.points[7].x += (self.head.x + 20 - self.points[7].x) * 0.03
                
                # Elbows bend up
                self.points[4].y += (self.head.y + 10 - self.points[4].y) * 0.03
                self.points[6].y += (self.head.y + 10 - self.points[6].y) * 0.03
                
                # Body trembles
                if random.random() < 0.2: self.head.x += random.choice([-1, 1])
                
            # Phase 2: ROPE SNAP & FALL
            elif self.death_timer == 120:
                self.rope_snapped = True
                # Remove rope constraint
                if self.rope in self.sticks:
                    self.sticks.remove(self.rope)
                self.head.locked = False # Ensure it falls
                # Add MASSIVE blood burst
                for _ in range(20):
                     self.blood_particles.append(BloodParticle(self.points[2].x, self.points[2].y))

            # Phase 3: LYING DEAD
            elif self.death_timer > 120:
                # Just gravity taking over (handled in Verlet loop)
                pass

    def draw(self, screen, wrong_count):
        self.wrong_count = wrong_count
        
        # Draw Blood
        for b in self.blood_particles:
            b.draw(screen)
            
        # Draw Rope (if not snapped)
        if not self.rope_snapped:
             pygame.draw.line(screen, ROPE_COLOR, (self.anchor.x, self.anchor.y), (self.head.x, self.head.y), 3)
        else:
             # Draw broken rope hanging from gallows
             pygame.draw.line(screen, ROPE_COLOR, (self.anchor.x, self.anchor.y), (self.anchor.x, self.anchor.y + 80), 3)
             # Draw broken rope attached to head (falling)
             pygame.draw.line(screen, ROPE_COLOR, (self.head.x, self.head.y), (self.head.x + 5, self.head.y - 30), 3)

        # 1. Head (Pop Scale)
        if wrong_count >= 1:
            scale = self.pop_progress[1]
            if scale > 0:
                radius = int(18 * scale)
                pygame.draw.circle(screen, STICKMAN_COLOR, (int(self.head.x), int(self.head.y)), radius, 2)
        
        # 2. Torso (Grow Down)
        if wrong_count >= 2:
            self._draw_stick_growing(screen, self.torso_stick, self.pop_progress[2])
            
        # 3. Left Arm (Grow Out)
        if wrong_count >= 3:
            prog = self.pop_progress[3]
            for s in self.l_arm_sticks: self._draw_stick_growing(screen, s, prog)
            # Draw Hand
            if prog > 0.8:
                pygame.draw.circle(screen, STICKMAN_COLOR, (int(self.points[5].x), int(self.points[5].y)), 4)
            
        # 4. Right Arm (Grow Out)
        if wrong_count >= 4:
            prog = self.pop_progress[4]
            for s in self.r_arm_sticks: self._draw_stick_growing(screen, s, prog)
            # Draw Hand
            if prog > 0.8:
                pygame.draw.circle(screen, STICKMAN_COLOR, (int(self.points[7].x), int(self.points[7].y)), 4)
            
        # 5. Left Leg (Grow Down)
        if wrong_count >= 5:
            prog = self.pop_progress[5]
            for s in self.l_leg_sticks: self._draw_stick_growing(screen, s, prog)
            # Draw Foot
            if prog > 0.8:
                pygame.draw.circle(screen, STICKMAN_COLOR, (int(self.points[9].x), int(self.points[9].y)), 4)
            
        # 6. Right Leg (Grow Down)
        if wrong_count >= 6:
            prog = self.pop_progress[6]
            for s in self.r_leg_sticks: self._draw_stick_growing(screen, s, prog)
            # Draw Foot
            if prog > 0.8:
                pygame.draw.circle(screen, STICKMAN_COLOR, (int(self.points[11].x), int(self.points[11].y)), 4)

    def _draw_stick_growing(self, screen, stick, progress):
        if progress <= 0: return
        start = (stick.p1.x, stick.p1.y)
        
        # Calculate grown end point
        end_x = stick.p1.x + (stick.p2.x - stick.p1.x) * progress
        end_y = stick.p1.y + (stick.p2.y - stick.p1.y) * progress
        end = (end_x, end_y)
        
        pygame.draw.line(screen, STICKMAN_COLOR, start, end, 4)

# ================= MAIN GAME CLASS =================
class HangmanGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.crypto = CryptoManager()
        
        self.state = "INTRO"
        self.ragdoll = Ragdoll(WIDTH//4, 100)  # Match gallows beam position
        
        self.word = ""
        self.encrypted_word = None
        self.guessed = set()
        self.wrong_count = 0
        self.status_msg = "Waiting..."
        self.attack_detected = False
        
        # Clean UI
        self.input_box = InputBox(WIDTH//2 - 150, HEIGHT//2 - 20, 300, 50, FONT_HEADING, is_password=True)
        self.input_box.color_inactive = (50, 50, 50)
        self.input_box.color_active = (100, 100, 100)
        
        self.btn_set = Button(WIDTH//2 - 120, HEIGHT//2 + 60, 240, 60, "ENCRYPT WORD", ACCENT, (255, 60, 60), self.set_word)
        self.btn_ready = Button(WIDTH//2 - 180, HEIGHT//2 + 100, 360, 70, "START GUESSING", SUCCESS, (20, 240, 120), self.start_guessing)
        self.btn_restart = Button(WIDTH - 220, HEIGHT - 100, 180, 60, "NEW GAME", DARK_BG, (30, 30, 30), self.reset_game)

    def reset_game(self):
        self.state = "SET_WORD"
        self.word = ""
        self.guessed = set()
        self.wrong_count = 0
        self.ragdoll = Ragdoll(WIDTH//4, 100)
        self.input_box.text = ""
        self.input_box.active = True
        self.attack_detected = False
        self.status_msg = "Player 1: Enter Secret Word"

    def set_word(self):
        text = self.input_box.text.strip().upper()
        if len(text) > 1 and text.isalpha():
            self.word = text
            self.encrypted_word = self.crypto.encrypt(text)
            self.state = "TRANSITION"
            self.status_msg = "Word Encrypted!"
            if random.random() < 0.2:
                self.attack_detected = True

    def start_guessing(self):
        self.state = "GUESSING"
        self.status_msg = "Integrity OK - Start Guessing!"
        if self.attack_detected:
            self.status_msg = "⚠️ INTEGRITY BREACH!"

    def handle_guess(self, char):
        if char in self.guessed or self.state != "GUESSING":
            return
        self.guessed.add(char)
        if char not in self.word:
            self.wrong_count += 1
            if self.wrong_count >= 6:
                self.state = "GAME_OVER"
                self.status_msg = "DEFEAT - Player 1 Wins!"
        else:
            if all(c in self.guessed for c in self.word):
                self.state = "GAME_OVER"
                self.status_msg = "VICTORY - Player 2 Wins!"

    def draw_intro(self):
        title = FONT_TITLE.render("HANGMAN", True, TEXT_WHITE)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 200))
        sub = FONT_BODY.render("Secure Communication Demo", True, TEXT_GRAY)
        self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 280))
        start = FONT_HEADING.render("Press SPACE to Start", True, ACCENT)
        self.screen.blit(start, (WIDTH//2 - start.get_width()//2, 400))

    def draw_set_word(self):
        title = FONT_HEADING.render("PLAYER 1: Set Secret Word", True, ACCENT)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 100))
        self.input_box.draw(self.screen)
        self.btn_set.draw(self.screen)
        note = FONT_SMALL.render("(Input hidden for security)", True, TEXT_GRAY)
        self.screen.blit(note, (WIDTH//2 - note.get_width()//2, HEIGHT//2 + 130))

    def draw_transition(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(DARK_BG)
        self.screen.blit(overlay, (0, 0))
        warn = FONT_TITLE.render("PLAYER 1 LOOK AWAY!", True, ACCENT)
        self.screen.blit(warn, (WIDTH//2 - warn.get_width()//2, HEIGHT//2 - 80))
        self.btn_ready.draw(self.screen)

    def draw_game(self):
        # 1. Left Side: Gallows (dark wood look)
        pygame.draw.line(self.screen, GALLOWS_COLOR, (40, 620), (320, 620), 8)  # Base
        pygame.draw.line(self.screen, GALLOWS_COLOR, (80, 620), (80, 80), 6)    # Pole
        pygame.draw.line(self.screen, GALLOWS_COLOR, (80, 80), (WIDTH//4, 80), 6) # Top beam
        pygame.draw.line(self.screen, GALLOWS_COLOR, (80, 140), (140, 80), 4)   # Support
        # Noose hint (always visible)
        pygame.draw.line(self.screen, ROPE_COLOR, (WIDTH//4, 80), (WIDTH//4, 100), 3) 
        
        self.ragdoll.update()
        self.ragdoll.draw(self.screen, self.wrong_count)
        
        # 2. Right Side: UI
        # Status
        status_col = ACCENT if "BREACH" in self.status_msg else TEXT_GRAY
        status_surf = FONT_BODY.render(f"STATUS: {self.status_msg}", True, status_col)
        self.screen.blit(status_surf, (450, 50))
        
        # Word
        display_word = []
        for char in self.word:
            if char in self.guessed or self.state == "GAME_OVER":
                display_word.append(char)
            else:
                display_word.append("_")
        
        word_txt = "  ".join(display_word)
        word_surf = FONT_WORD.render(word_txt, True, TEXT_WHITE)
        self.screen.blit(word_surf, (450, 150))
        
        # Keyboard
        start_x, start_y = 450, 300
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, char in enumerate(letters):
            row = i // 7
            col = i % 7
            x = start_x + col * 75
            y = start_y + row * 75
            
            # Button Colors
            bg_col = (15, 15, 15)
            border_col = (40, 40, 40)
            txt_col = TEXT_GRAY
            
            if char in self.guessed:
                if char in self.word:
                    bg_col = (0, 100, 50)
                    border_col = SUCCESS
                    txt_col = TEXT_WHITE
                else:
                    bg_col = (60, 10, 10)
                    border_col = ACCENT
                    txt_col = (150, 50, 50)
            
            # Draw Key
            rect = pygame.Rect(x, y, 65, 65)
            pygame.draw.rect(self.screen, bg_col, rect, border_radius=12)
            pygame.draw.rect(self.screen, border_col, rect, 2, border_radius=12)
            
            char_surf = FONT_HEADING.render(char, True, txt_col)
            char_rect = char_surf.get_rect(center=rect.center)
            self.screen.blit(char_surf, char_rect)
            
        if self.state == "GAME_OVER":
            if self.wrong_count >= 6:
                t = FONT_TITLE.render("DEFEAT", True, ACCENT)
                st = FONT_BODY.render(f"Word was: {self.word}", True, TEXT_WHITE)
                
                # Draw "Dying in Regret" text maybe? Or keep it subtle
                regret_txt = FONT_SMALL.render("The stickman perished in despair...", True, (100, 50, 50))
                self.screen.blit(regret_txt, (100, 50)) # near gallows
            else:
                t = FONT_TITLE.render("VICTORY", True, SUCCESS)
                st = FONT_BODY.render("Encryption Verified", True, TEXT_GRAY)

            self.screen.blit(t, (450, 600))
            self.screen.blit(st, (450, 660))
            self.btn_restart.draw(self.screen)

    def run(self):
        running = True
        while running:
            pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Global Keyboard Handling for Game Logic
                if event.type == pygame.KEYDOWN:
                    if self.state == "INTRO" and event.key == pygame.K_SPACE:
                        self.reset_game()
                    
                    elif self.state == "GUESSING":
                        if event.unicode.isalpha():
                            self.handle_guess(event.unicode.upper())
                
                # UI Event Handling
                if self.state == "SET_WORD":
                    res = self.input_box.handle_event(event)
                    if res: # Enter presesd
                        self.set_word()
                    self.btn_set.check_hover(pos)
                    if event.type == pygame.MOUSEBUTTONDOWN and self.btn_set.is_hovered:
                        self.btn_set.click()
                
                elif self.state == "TRANSITION":
                    self.btn_ready.check_hover(pos)
                    if event.type == pygame.MOUSEBUTTONDOWN and self.btn_ready.is_hovered:
                        self.btn_ready.click()
                
                elif self.state == "GAME_OVER":
                    self.btn_restart.check_hover(pos)
                    if event.type == pygame.MOUSEBUTTONDOWN and self.btn_restart.is_hovered:
                        self.btn_restart.click()
            
            # Drawing
            self.screen.fill(DARK_BG)
            
            if self.state == "INTRO":
                self.draw_intro()
            elif self.state == "SET_WORD":
                self.draw_set_word()
            elif self.state == "TRANSITION":
                self.draw_set_word() # Keep BG
                self.draw_transition() # Overlay
            elif self.state in ["GUESSING", "GAME_OVER"]:
                self.draw_game()
                
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = HangmanGame()
    game.run()
