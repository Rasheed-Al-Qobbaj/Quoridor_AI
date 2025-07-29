import pygame
import sys
from collections import deque
import math
import threading  # For running the AI without freezing the UI
import time  # For getting the AI calculation time

# --- Constants ---
# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
LIGHT_BROWN = (205, 133, 63)
PLAYER1_COLOR = (0, 0, 255)
PLAYER2_COLOR = (255, 0, 0)
HIGHLIGHT_COLOR = (255, 255, 0)
WALL_COLOR = BLACK
ERROR_COLOR = (200, 0, 0)
BUTTON_COLOR = (50, 50, 50)
BUTTON_HOVER_COLOR = (100, 100, 100)

# Screen Dimensions
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 700
HUD_HEIGHT = 100

# Board Dimensions
BOARD_SIZE = 9
SQUARE_SIZE = SCREEN_WIDTH // (BOARD_SIZE + 1)
WALL_THICKNESS = SQUARE_SIZE // 5
BOARD_OFFSET_X = SQUARE_SIZE // 2
BOARD_OFFSET_Y = SQUARE_SIZE // 2 + HUD_HEIGHT


class AI:
    def __init__(self, game):
        self.game = game  # Give the AI a reference to the main game object

    def get_shortest_path(self, start_pos, goal_row, opponent_pos):
        # BFS that returns the path length
        q = deque([(start_pos, 0)])  # (position, distance)
        visited = {start_pos}

        while q:
            current_pos, dist = q.popleft()

            if current_pos[1] == goal_row:
                return dist  # Return the distance when the goal is found

            # Note: We must use the game's full move calculation
            valid_moves = self.game.calculate_valid_moves(current_pos, opponent_pos)
            for neighbor in valid_moves:
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append((neighbor, dist + 1))

        return math.inf  # Return infinity if no path exists

    def evaluate_board(self, player1_pos, player2_pos):
        # The AI is always Player 2
        p1_path_len = self.get_shortest_path(player1_pos, self.game.player1_goal_row, player2_pos)
        p2_path_len = self.get_shortest_path(player2_pos, self.game.player2_goal_row, player1_pos)

        # Heuristic: Difference in path lengths. Higher is better for AI (Player 2).
        return p1_path_len - p2_path_len

    def find_best_move(self):
        # We will replace this with Minimax later
        best_score = -math.inf
        best_move = None
        current_pawn_pos = self.game.player2_pos
        opponent_pawn_pos = self.game.player1_pos
        possible_pawn_moves = self.game.calculate_valid_moves(current_pawn_pos, opponent_pawn_pos)

        for move in possible_pawn_moves:
            score = self.evaluate_board(opponent_pawn_pos, move)
            if score > best_score:
                best_score = score
                best_move = ('pawn', move)

        if best_move is None and possible_pawn_moves:
            best_move = ('pawn', possible_pawn_moves[0])

        # The AI thread will store its result here
        self.game.ai_move_result = best_move


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Quoridor')
        self.font = pygame.font.SysFont(None, 50)
        self.hud_font = pygame.font.SysFont(None, 40)
        self.title_font = pygame.font.SysFont(None, 100)
        self.game_over_font = pygame.font.SysFont(None, 80)

        self.game_state = 'main_menu'  # 'main_menu', 'playing', 'game_over'
        self.game_mode = None  # 'pvp', 'pvai', 'aivai'

        self.pvp_button = pygame.Rect(150, 250, 300, 60)
        self.pvai_button = pygame.Rect(150, 350, 300, 60)
        self.aivai_button = pygame.Rect(150, 450, 300, 60)
        self.ai = AI(self)

        # State variables for AI thinking animation and timing
        self.ai_is_thinking = False
        self.ai_thread = None
        self.ai_move_result = None
        self.ai_start_time = 0
        self.ai_time_taken = 0
        self.ai_time_display_end_time = 0
        self.thinking_animation_angle = 0

        self.reset_game()

    def reset_game(self):
        # Game State
        self.player1_pos = (4, 8)
        self.player2_pos = (4, 0)
        self.player1_walls = 10
        self.player2_walls = 10
        self.horizontal_walls = set()
        self.vertical_walls = set()
        self.current_player = 1
        self.selected_pawn = None
        self.valid_moves = []
        self.player1_goal_row = 0
        self.player2_goal_row = 8
        self.error_message = ""
        self.error_message_end_time = 0
        self.winner = None
        self.game_over = False

    def draw_main_menu(self):
        self.screen.fill(BROWN)
        mouse_pos = pygame.mouse.get_pos()

        title_text = self.title_font.render("Quoridor", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, 120))
        self.screen.blit(title_text, title_rect)

        pvp_color = BUTTON_HOVER_COLOR if self.pvp_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(self.screen, pvp_color, self.pvp_button, border_radius=10)
        pvp_text = self.font.render("Player vs Player", True, WHITE)
        pvp_text_rect = pvp_text.get_rect(center=self.pvp_button.center)
        self.screen.blit(pvp_text, pvp_text_rect)

        pvai_color = BUTTON_HOVER_COLOR if self.pvai_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(self.screen, pvai_color, self.pvai_button, border_radius=10)
        pvai_text = self.font.render("Player vs AI", True, WHITE)
        pvai_text_rect = pvai_text.get_rect(center=self.pvai_button.center)
        self.screen.blit(pvai_text, pvai_text_rect)

        aivai_color = BUTTON_HOVER_COLOR if self.aivai_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(self.screen, aivai_color, self.aivai_button, border_radius=10)
        aivai_text = self.font.render("AI vs AI", True, WHITE)
        aivai_text_rect = aivai_text.get_rect(center=self.aivai_button.center)
        self.screen.blit(aivai_text, aivai_text_rect)

    def get_square_from_pos(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = BOARD_OFFSET_X + col * SQUARE_SIZE
                y = BOARD_OFFSET_Y + row * SQUARE_SIZE
                rect = pygame.Rect(x, y, SQUARE_SIZE - WALL_THICKNESS, SQUARE_SIZE - WALL_THICKNESS)
                if rect.collidepoint(mouse_x, mouse_y):
                    return (col, row)
        return None

    def get_wall_from_pos(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        for r in range(BOARD_SIZE - 1):
            for c in range(BOARD_SIZE - 1):
                x = BOARD_OFFSET_X + c * SQUARE_SIZE
                y = BOARD_OFFSET_Y + r * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS)
                rect = pygame.Rect(x, y, SQUARE_SIZE * 2 - WALL_THICKNESS, WALL_THICKNESS)
                if rect.collidepoint(mouse_x, mouse_y):
                    return ('h', (c, r))
        for r in range(BOARD_SIZE - 1):
            for c in range(BOARD_SIZE - 1):
                x = BOARD_OFFSET_X + c * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS)
                y = BOARD_OFFSET_Y + r * SQUARE_SIZE
                rect = pygame.Rect(x, y, WALL_THICKNESS, SQUARE_SIZE * 2 - WALL_THICKNESS)
                if rect.collidepoint(mouse_x, mouse_y):
                    return ('v', (c, r))
        return None

    def calculate_valid_moves(self, pawn_pos, opponent_pos):
        moves = []
        c, r = pawn_pos
        oc, or_ = opponent_pos

        # Directions: (dc, dr) -> change in col, change in row
        for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            next_pos = (c + dc, r + dr)

            # First, check if the immediate path is blocked by a wall.
            # If it is, this direction is invalid for any type of move.
            if self.is_wall_blocking(pawn_pos, next_pos):
                continue

            # --- Check for opponent ---
            if next_pos == opponent_pos:
                # If path to opponent is clear, calculate jumps from the opponent's position
                jump_pos = (oc + dc, or_ + dr)

                # Is the forward jump blocked by a wall?
                if self.is_wall_blocking(opponent_pos, jump_pos) or not (
                        0 <= jump_pos[0] < BOARD_SIZE and 0 <= jump_pos[1] < BOARD_SIZE):
                    # Jump is blocked, check for sideways moves
                    if dc == 0:  # Vertical jump was blocked
                        # Check LEFT of opponent
                        if not self.is_wall_blocking(opponent_pos, (oc - 1, or_)):
                            if 0 <= oc - 1 < BOARD_SIZE: moves.append((oc - 1, or_))
                        # Check RIGHT of opponent
                        if not self.is_wall_blocking(opponent_pos, (oc + 1, or_)):
                            if 0 <= oc + 1 < BOARD_SIZE: moves.append((oc + 1, or_))
                    else:  # Horizontal jump was blocked
                        # Check UP from opponent
                        if not self.is_wall_blocking(opponent_pos, (oc, or_ - 1)):
                            if 0 <= or_ - 1 < BOARD_SIZE: moves.append((oc, or_ - 1))
                        # Check DOWN from opponent
                        if not self.is_wall_blocking(opponent_pos, (oc, or_ + 1)):
                            if 0 <= or_ + 1 < BOARD_SIZE: moves.append((oc, or_ + 1))
                else:
                    # Forward jump is valid
                    moves.append(jump_pos)

                # After handling jump logic, move to the next direction
                continue

            # --- Standard move (if not a wall and not an opponent) ---
            if 0 <= next_pos[0] < BOARD_SIZE and 0 <= next_pos[1] < BOARD_SIZE:
                moves.append(next_pos)

        return list(set(moves))  # Use set to remove duplicates from complex jump cases

    def path_exists(self, start_pos, goal_row, opponent_pos):
        q = deque([start_pos])
        visited = {start_pos}
        while q:
            current_pos = q.popleft()
            if current_pos[1] == goal_row: return True
            for neighbor in self.calculate_valid_moves(current_pos, opponent_pos):
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        return False

    def is_wall_blocking(self, start_pos, end_pos):
        sc, sr = start_pos
        ec, er = end_pos
        if abs(sc - ec) + abs(sr - er) > 1:
            return False
        if sc == ec:
            if er < sr:
                return (sc, er) in self.horizontal_walls or (sc - 1, er) in self.horizontal_walls
            else:
                return (sc, sr) in self.horizontal_walls or (sc - 1, sr) in self.horizontal_walls
        if sr == er:
            if ec < sc:
                return (ec, sr) in self.vertical_walls or (ec, sr - 1) in self.vertical_walls
            else:
                return (sc, sr) in self.vertical_walls or (sc, sr - 1) in self.vertical_walls
        return False

    def is_valid_wall_placement(self, wall_type, pos):
        c, r = pos
        if wall_type == 'h':
            if (c, r) in self.horizontal_walls or (c - 1, r) in self.horizontal_walls or (
            c + 1, r) in self.horizontal_walls: return False
            if (c, r) in self.vertical_walls: return False
        elif wall_type == 'v':
            if (c, r) in self.vertical_walls or (c, r - 1) in self.vertical_walls or (
            c, r + 1) in self.vertical_walls: return False
            if (c, r) in self.horizontal_walls: return False
        return True

    def draw_board(self):
        self.screen.fill(BROWN)
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = BOARD_OFFSET_X + col * SQUARE_SIZE
                y = BOARD_OFFSET_Y + row * SQUARE_SIZE
                rect = pygame.Rect(x, y, SQUARE_SIZE - WALL_THICKNESS, SQUARE_SIZE - WALL_THICKNESS)
                pygame.draw.rect(self.screen, LIGHT_BROWN, rect)

    def draw_walls(self):
        for c, r in self.horizontal_walls:
            x = BOARD_OFFSET_X + c * SQUARE_SIZE
            y = BOARD_OFFSET_Y + r * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS)
            rect = pygame.Rect(x, y, SQUARE_SIZE * 2 - WALL_THICKNESS, WALL_THICKNESS)
            pygame.draw.rect(self.screen, WALL_COLOR, rect)

        for c, r in self.vertical_walls:
            x = BOARD_OFFSET_X + c * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS)
            y = BOARD_OFFSET_Y + r * SQUARE_SIZE
            rect = pygame.Rect(x, y, WALL_THICKNESS, SQUARE_SIZE * 2 - WALL_THICKNESS)
            pygame.draw.rect(self.screen, WALL_COLOR, rect)

    def draw_pawns(self):
        p1_x = BOARD_OFFSET_X + self.player1_pos[0] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
        p1_y = BOARD_OFFSET_Y + self.player1_pos[1] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
        pygame.draw.circle(self.screen, PLAYER1_COLOR, (p1_x, p1_y), SQUARE_SIZE / 3)
        p2_x = BOARD_OFFSET_X + self.player2_pos[0] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
        p2_y = BOARD_OFFSET_Y + self.player2_pos[1] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
        pygame.draw.circle(self.screen, PLAYER2_COLOR, (p2_x, p2_y), SQUARE_SIZE / 3)

    def draw_valid_moves(self):
        for move in self.valid_moves:
            col, row = move
            x = BOARD_OFFSET_X + col * SQUARE_SIZE
            y = BOARD_OFFSET_Y + row * SQUARE_SIZE
            rect = pygame.Rect(x + 5, y + 5, SQUARE_SIZE - WALL_THICKNESS - 10, SQUARE_SIZE - WALL_THICKNESS - 10)
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, rect, 3)

    def draw_ai_status(self):
        # Determine the center for the AI status information
        status_center_x = SCREEN_WIDTH * 3 / 4

        if self.ai_is_thinking:
            # Draw "AI is thinking..." text
            thinking_text = self.hud_font.render("AI is thinking...", True, PLAYER2_COLOR)
            thinking_rect = thinking_text.get_rect(center=(status_center_x, 35))
            self.screen.blit(thinking_text, thinking_rect)

            # Draw a rotating arc as a loading animation
            arc_center = (status_center_x, 70)
            arc_rect = pygame.Rect(arc_center[0] - 15, arc_center[1] - 15, 30, 30)
            start_angle = math.radians(self.thinking_animation_angle)
            end_angle = math.radians(self.thinking_animation_angle + 270)
            pygame.draw.arc(self.screen, WHITE, arc_rect, start_angle, end_angle, 4)
            self.thinking_animation_angle = (self.thinking_animation_angle - 15) % 360
        else:
            if time.time() < self.ai_time_display_end_time:
                time_text_str = f"Time: {self.ai_time_taken:.3f}s"
                time_text = self.hud_font.render(time_text_str, True, WHITE)
                time_rect = time_text.get_rect(center=(status_center_x, 100))
                self.screen.blit(time_text, time_rect)

    def draw_hud(self):
        # Player 1's Turn indicator (always on the left)
        if self.current_player == 1:
            turn_text = self.font.render("Your Turn", True, PLAYER1_COLOR)
            turn_rect = turn_text.get_rect(center=(SCREEN_WIDTH / 4, 35))
            self.screen.blit(turn_text, turn_rect)

        # AI Status / Player 2's Turn indicator (always on the right)
        if self.game_mode == 'pvai':
            self.draw_ai_status()
        elif self.current_player == 2:  # PvP mode
            turn_text = self.font.render("P2's Turn", True, PLAYER2_COLOR)
            turn_rect = turn_text.get_rect(center=(SCREEN_WIDTH * 3 / 4, 35))
            self.screen.blit(turn_text, turn_rect)

        # Wall counts (always at the bottom of HUD)
        p1_wall_text_str = f"Walls: {self.player1_walls}"
        p1_wall_text = self.hud_font.render(p1_wall_text_str, True, PLAYER1_COLOR)
        p1_wall_rect = p1_wall_text.get_rect(center=(SCREEN_WIDTH / 4, 70))
        self.screen.blit(p1_wall_text, p1_wall_rect)
        p2_wall_text_str = f"Walls: {self.player2_walls}"
        p2_wall_text = self.hud_font.render(p2_wall_text_str, True, PLAYER2_COLOR)
        p2_wall_rect = p2_wall_text.get_rect(center=(SCREEN_WIDTH * 3 / 4, 70))
        self.screen.blit(p2_wall_text, p2_wall_rect)

    def draw_error_message(self):
        current_time = pygame.time.get_ticks()
        if current_time < self.error_message_end_time:
            error_text = self.hud_font.render(self.error_message, True, ERROR_COLOR)
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH / 2, HUD_HEIGHT - 20))
            self.screen.blit(error_text, error_rect)

    def draw_game_over_screen(self):
        if self.game_state != 'game_over':
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))  # Black with 150/255 alpha
        self.screen.blit(overlay, (0, 0))

        winner_text_str = f"Player {self.winner} Wins!"
        winner_color = PLAYER1_COLOR if self.winner == 1 else PLAYER2_COLOR
        winner_text = self.game_over_font.render(winner_text_str, True, winner_color)
        winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
        self.screen.blit(winner_text, winner_rect)

        restart_text_str = "Click to Return to Menu"
        restart_text = self.font.render(restart_text_str, True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50))
        self.screen.blit(restart_text, restart_rect)

    def handle_click(self, mouse_pos):
        if self.ai_is_thinking:
            return

        if self.game_state == 'main_menu':
            if self.pvp_button.collidepoint(mouse_pos):
                self.game_mode = 'pvp'
                self.game_state = 'playing'
                self.reset_game()
            elif self.pvai_button.collidepoint(mouse_pos):
                self.game_mode = 'pvai'
                self.game_state = 'playing'
                self.reset_game()
            elif self.aivai_button.collidepoint(mouse_pos):
                self.game_mode = 'aivai'
                self.game_state = 'playing'
                self.reset_game()
        elif self.game_state == 'playing':
            is_human_turn = (self.game_mode == 'pvp' or
                             (self.game_mode == 'pvai' and self.current_player == 1))
            if is_human_turn:
                self.handle_player_move(mouse_pos)
        elif self.game_state == 'game_over':
            self.game_state = 'main_menu'

    def handle_player_move(self, mouse_pos):
        self.selected_pawn = None
        self.valid_moves = []
        clicked_square = self.get_square_from_pos(mouse_pos)
        clicked_wall = self.get_wall_from_pos(mouse_pos)

        current_pawn_pos = self.player1_pos if self.current_player == 1 else self.player2_pos
        opponent_pos = self.player2_pos if self.current_player == 1 else self.player1_pos
        current_valid_moves = self.calculate_valid_moves(current_pawn_pos, opponent_pos)

        if clicked_square:
            if clicked_square == current_pawn_pos:
                self.selected_pawn = current_pawn_pos
                self.valid_moves = current_valid_moves
            elif clicked_square in current_valid_moves:
                self.execute_move(('pawn', clicked_square))
        elif clicked_wall:
            self.execute_move(('wall', clicked_wall))

    def execute_move(self, move):
        move_type, move_data = move

        if move_type == 'pawn':
            moving_player = self.current_player
            if moving_player == 1:
                self.player1_pos = move_data
            else:
                self.player2_pos = move_data

            pawn_pos = self.player1_pos if moving_player == 1 else self.player2_pos
            goal_row = self.player1_goal_row if moving_player == 1 else self.player2_goal_row

            if pawn_pos[1] == goal_row:
                self.winner = moving_player
                self.game_state = 'game_over'
            else:
                self.current_player = 3 - self.current_player

        elif move_type == 'wall':
            wall_type, pos = move_data
            player_walls = self.player1_walls if self.current_player == 1 else self.player2_walls

            if player_walls > 0 and self.is_valid_wall_placement(wall_type, pos):
                if wall_type == 'h':
                    self.horizontal_walls.add(pos)
                else:
                    self.vertical_walls.add(pos)

                if self.path_exists(self.player1_pos, self.player1_goal_row, self.player2_pos) and \
                        self.path_exists(self.player2_pos, self.player2_goal_row, self.player1_pos):
                    if self.current_player == 1:
                        self.player1_walls -= 1
                    else:
                        self.player2_walls -= 1
                    self.current_player = 3 - self.current_player
                else:  # Illegal block
                    self.error_message = "Wall must not block all paths!"
                    self.error_message_end_time = pygame.time.get_ticks() + 3000
                    if wall_type == 'h':
                        self.horizontal_walls.remove(pos)
                    else:
                        self.vertical_walls.remove(pos)

    def run(self):
        running = True
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(pygame.mouse.get_pos())

            # AI Turn Logic
            is_ai_turn = (self.game_state == 'playing' and
                          self.game_mode == 'pvai' and
                          self.current_player == 2 and
                          not self.ai_is_thinking)

            if is_ai_turn:
                self.ai_is_thinking = True
                self.ai_move_result = None
                self.ai_thread = threading.Thread(target=self.ai.find_best_move, daemon=True)
                self.ai_start_time = time.time()
                self.ai_thread.start()

            # Check if AI has finished
            if self.ai_is_thinking and not self.ai_thread.is_alive():
                self.ai_time_taken = time.time() - self.ai_start_time
                self.ai_time_display_end_time = time.time() + 4  # Show for 4 seconds
                self.ai_is_thinking = False
                if self.ai_move_result:
                    self.execute_move(self.ai_move_result)

            # Drawing logic
            self.screen.fill(BROWN)
            if self.game_state == 'main_menu':
                self.draw_main_menu()
            elif self.game_state == 'playing' or self.game_state == 'game_over':
                self.draw_board()
                self.draw_walls()
                if self.game_state == 'playing':
                    self.draw_valid_moves()
                self.draw_pawns()
                self.draw_hud()
                self.draw_error_message()
                if self.game_state == 'game_over':
                    self.draw_game_over_screen()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    game = Game()
    game.run()