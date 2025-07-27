import pygame
import sys
from collections import deque

# --- Constants ---
# ... (No changes)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
LIGHT_BROWN = (205, 133, 63)
PLAYER1_COLOR = (0, 0, 255)  # Blue
PLAYER2_COLOR = (255, 0, 0)  # Red
HIGHLIGHT_COLOR = (255, 255, 0)  # Yellow
WALL_COLOR = BLACK
ERROR_COLOR = (200, 0, 0)
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 700
HUD_HEIGHT = 100
BOARD_SIZE = 9
SQUARE_SIZE = SCREEN_WIDTH // (BOARD_SIZE + 1)
WALL_THICKNESS = SQUARE_SIZE // 5
BOARD_OFFSET_X = SQUARE_SIZE // 2
BOARD_OFFSET_Y = SQUARE_SIZE // 2 + HUD_HEIGHT


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Quoridor')
        self.font = pygame.font.SysFont(None, 50)
        self.hud_font = pygame.font.SysFont(None, 40)
        ## NEW: Larger font for the game over message
        self.game_over_font = pygame.font.SysFont(None, 80)

        self.reset_game()

    ## NEW: A function to reset the game to its initial state.
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

        ## NEW: Game over state tracking
        self.game_over = False
        self.winner = None

    # ... (getters, calculations, and is_... functions are all unchanged)
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
        for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            next_pos = (c + dc, r + dr)
            if next_pos == opponent_pos:
                jump_pos = (oc + dc, or_ + dr)
                if 0 <= jump_pos[0] < BOARD_SIZE and 0 <= jump_pos[1] < BOARD_SIZE and not self.is_wall_blocking(
                        opponent_pos, jump_pos):
                    moves.append(jump_pos)
                else:
                    if dc == 0:
                        if 0 <= oc - 1 < BOARD_SIZE and not self.is_wall_blocking(opponent_pos,
                                                                                  (oc - 1, or_)): moves.append(
                            (oc - 1, or_))
                        if 0 <= oc + 1 < BOARD_SIZE and not self.is_wall_blocking(opponent_pos,
                                                                                  (oc + 1, or_)): moves.append(
                            (oc + 1, or_))
                    else:
                        if 0 <= or_ - 1 < BOARD_SIZE and not self.is_wall_blocking(opponent_pos,
                                                                                   (oc, or_ - 1)): moves.append(
                            (oc, or_ - 1))
                        if 0 <= or_ + 1 < BOARD_SIZE and not self.is_wall_blocking(opponent_pos,
                                                                                   (oc, or_ + 1)): moves.append(
                            (oc, or_ + 1))
                continue
            if 0 <= next_pos[0] < BOARD_SIZE and 0 <= next_pos[1] < BOARD_SIZE:
                if not self.is_wall_blocking(pawn_pos, next_pos):
                    moves.append(next_pos)
        return list(set(moves))

    def path_exists(self, start_pos, goal_row, opponent_pos):
        q = deque([start_pos])
        visited = {start_pos}
        while q:
            current_pos = q.popleft()
            if current_pos[1] == goal_row:
                return True
            for neighbor in self.calculate_valid_moves(current_pos, opponent_pos):
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        return False

    def is_wall_blocking(self, start_pos, end_pos):
        sc, sr = start_pos
        ec, er = end_pos
        if abs(sc - ec) + abs(sr - er) > 1: return False
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

    # ... (draw functions are mostly unchanged)
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

    def draw_hud(self):
        turn_text_str = f"Player {self.current_player}'s Turn"
        turn_color = PLAYER1_COLOR if self.current_player == 1 else PLAYER2_COLOR
        turn_text = self.font.render(turn_text_str, True, turn_color)
        turn_text_rect = turn_text.get_rect(center=(SCREEN_WIDTH / 2, 30))
        self.screen.blit(turn_text, turn_text_rect)
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

    ## NEW: Renders the game over screen when a winner is decided
    def draw_game_over_screen(self):
        if not self.game_over:
            return

        # Create a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))  # Black with 150/255 alpha
        self.screen.blit(overlay, (0, 0))

        winner_text_str = f"Player {self.winner} Wins!"
        winner_color = PLAYER1_COLOR if self.winner == 1 else PLAYER2_COLOR
        winner_text = self.game_over_font.render(winner_text_str, True, winner_color)
        winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
        self.screen.blit(winner_text, winner_rect)

        restart_text_str = "Click to Play Again"
        restart_text = self.font.render(restart_text_str, True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50))
        self.screen.blit(restart_text, restart_rect)

    ## MODIFIED: Now handles game restart and checks for win condition
    def handle_click(self, mouse_pos):
        ## NEW: If game is over, any click will restart it
        if self.game_over:
            self.reset_game()
            return

        self.selected_pawn = None
        self.valid_moves = []

        clicked_square = self.get_square_from_pos(mouse_pos)
        clicked_wall = self.get_wall_from_pos(mouse_pos)
        current_pawn_pos = self.player1_pos if self.current_player == 1 else self.player2_pos
        opponent_pos = self.player2_pos if self.current_player == 1 else self.player1_pos
        current_valid_moves = self.calculate_valid_moves(current_pawn_pos, opponent_pos)

        # Handle Pawn Movement
        if clicked_square:
            if clicked_square == current_pawn_pos:
                self.selected_pawn = current_pawn_pos
                self.valid_moves = current_valid_moves
            elif clicked_square in current_valid_moves:
                moving_player = self.current_player
                if moving_player == 1:
                    self.player1_pos = clicked_square
                else:
                    self.player2_pos = clicked_square

                # Check for win condition
                if moving_player == 1 and self.player1_pos[1] == self.player1_goal_row:
                    self.game_over = True
                    self.winner = 1
                elif moving_player == 2 and self.player2_pos[1] == self.player2_goal_row:
                    self.game_over = True
                    self.winner = 2

                if not self.game_over:
                    self.current_player = 3 - self.current_player

        # Handle Wall Placement
        elif clicked_wall:
            # ... wall placement logic is unchanged, but is now skipped if game is over
            # ...

            wall_type, pos = clicked_wall
            player_walls = self.player1_walls if self.current_player == 1 else self.player2_walls
            if player_walls <= 0:
                self.error_message = "You have no walls left!"
                self.error_message_end_time = pygame.time.get_ticks() + 2000
                return
            if not self.is_valid_wall_placement(wall_type, pos):
                self.error_message = "Cannot place a wall that overlaps another."
                self.error_message_end_time = pygame.time.get_ticks() + 2500
                return
            if wall_type == 'h':
                self.horizontal_walls.add(pos)
            else:
                self.vertical_walls.add(pos)
            p1_has_path = self.path_exists(self.player1_pos, self.player1_goal_row, self.player2_pos)
            p2_has_path = self.path_exists(self.player2_pos, self.player2_goal_row, self.player1_pos)
            if p1_has_path and p2_has_path:
                if self.current_player == 1:
                    self.player1_walls -= 1
                else:
                    self.player2_walls -= 1
                self.current_player = 3 - self.current_player
            else:
                self.error_message = "Wall must not block all paths to the goal!"
                self.error_message_end_time = pygame.time.get_ticks() + 3000
                if wall_type == 'h':
                    self.horizontal_walls.remove(pos)
                else:
                    self.vertical_walls.remove(pos)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(pygame.mouse.get_pos())

            # Drawing logic
            self.draw_board()
            self.draw_walls()
            self.draw_valid_moves()
            self.draw_pawns()
            self.draw_hud()
            self.draw_error_message()
            ## NEW: Draw the game over screen on top of everything else
            self.draw_game_over_screen()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    game = Game()
    game.run()