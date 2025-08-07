import pygame
import sys
from collections import deque
import math
import threading
import time

# --- Constants ---
# Colors
WHITE = (236, 236, 236)
BLACK = (20, 20, 20)
BROWN = (39, 28, 19)
LIGHT_BROWN = (210, 180, 140)
PLAYER1_COLOR = (65, 105, 225)
PLAYER2_COLOR = (220, 20, 60)
HIGHLIGHT_COLOR = (255, 215, 0)
WALL_COLOR = (184, 134, 11)
ERROR_COLOR = (200, 0, 0)
BUTTON_COLOR = (50, 50, 50)
BUTTON_HOVER_COLOR = (100, 100, 100)

# Screen Dimensions
SCREEN_WIDTH = 650
SCREEN_HEIGHT = 750
HUD_HEIGHT = 100

# Board Dimensions
BOARD_SIZE = 9
SQUARE_SIZE = SCREEN_WIDTH // (BOARD_SIZE + 1)
WALL_THICKNESS = SQUARE_SIZE // 5
BOARD_OFFSET_X = SQUARE_SIZE // 2
BOARD_OFFSET_Y = SQUARE_SIZE // 2 + HUD_HEIGHT


class AI:
    def __init__(self, game, player_number):
        self.game = game
        self.player_number = player_number
        self.move_order_cache = []

    def is_valid_wall_in_sim(self, wall_type, pos, h_walls, v_walls):
        c, r = pos
        if not (0 <= c < BOARD_SIZE - 1 and 0 <= r < BOARD_SIZE - 1):
            return False
        if wall_type == 'h':
            if (c, r) in h_walls or (c - 1, r) in h_walls or (c + 1, r) in h_walls: return False
            if (c, r) in v_walls: return False
        elif wall_type == 'v':
            if (c, r) in v_walls or (c, r - 1) in v_walls or (c, r + 1) in v_walls: return False
            if (c, r) in h_walls: return False
        return True

    def get_shortest_path(self, start_pos, goal_row, opponent_pos, h_walls, v_walls):
        q = deque([(start_pos, 0)])
        visited = {start_pos}
        original_h, original_v = self.game.horizontal_walls, self.game.vertical_walls
        self.game.horizontal_walls, self.game.vertical_walls = h_walls, v_walls
        path_dist = math.inf
        while q:
            current_pos, dist = q.popleft()
            if current_pos[1] == goal_row:
                path_dist = dist
                break
            for neighbor in self.game.calculate_valid_moves(current_pos, opponent_pos):
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append((neighbor, dist + 1))
        self.game.horizontal_walls, self.game.vertical_walls = original_h, original_v
        return path_dist

    def evaluate_board(self, p1_pos, p2_pos, p1_walls, p2_walls, h_walls, v_walls):
        p1_path = self.get_shortest_path(p1_pos, self.game.player1_goal_row, p2_pos, h_walls, v_walls)
        p2_path = self.get_shortest_path(p2_pos, self.game.player2_goal_row, p1_pos, h_walls, v_walls)

        if p1_path == 0: return -math.inf
        if p2_path == 0: return math.inf

        return p1_path - p2_path

    def _get_possible_moves(self, player_pos, opponent_pos, walls_left, h_walls, v_walls):
        pawn_moves = self.game.calculate_valid_moves(player_pos, opponent_pos)
        all_moves = [('pawn', move) for move in pawn_moves]

        if walls_left > 0:
            oc, or_ = opponent_pos
            for r_offset in range(-2, 3):
                for c_offset in range(-2, 3):
                    h_pos, v_pos = (oc + c_offset, or_ + r_offset), (oc + c_offset, or_ + r_offset)
                    if self.is_valid_wall_in_sim('h', h_pos, h_walls, v_walls):
                        all_moves.append(('wall', ('h', h_pos)))
                    if self.is_valid_wall_in_sim('v', v_pos, h_walls, v_walls):
                        all_moves.append(('wall', ('v', v_pos)))
        return all_moves

    def minimax(self, p1_pos, p2_pos, p1_walls, p2_walls, h_walls, v_walls, depth, alpha, beta, is_p2_turn):
        is_game_over = p1_pos[1] == self.game.player1_goal_row or p2_pos[1] == self.game.player2_goal_row
        if depth == 0 or is_game_over:
            return self.evaluate_board(p1_pos, p2_pos, p1_walls, p2_walls, h_walls, v_walls), None

        best_move = None
        if is_p2_turn:
            max_eval = -math.inf
            moves = self._get_possible_moves(p2_pos, p1_pos, p2_walls, h_walls, v_walls)
            if self.move_order_cache: moves.sort(key=lambda m: self.move_order_cache[0] == m, reverse=True)
            for move_type, move_data in moves:
                h_copy, v_copy = h_walls.copy(), v_walls.copy()
                if move_type == 'pawn':
                    eval_val, _ = self.minimax(p1_pos, move_data, p1_walls, p2_walls, h_copy, v_copy, depth - 1, alpha,
                                               beta, False)
                else:
                    wall_type, pos = move_data
                    if wall_type == 'h':
                        h_copy.add(pos)
                    else:
                        v_copy.add(pos)
                    p1_path = self.get_shortest_path(p1_pos, self.game.player1_goal_row, p2_pos, h_copy, v_copy)
                    p2_path = self.get_shortest_path(p2_pos, self.game.player2_goal_row, p1_pos, h_copy, v_copy)
                    if p1_path == math.inf or p2_path == math.inf:
                        eval_val = -math.inf
                    else:
                        eval_val, _ = self.minimax(p1_pos, p2_pos, p1_walls, p2_walls - 1, h_copy, v_copy, depth - 1,
                                                   alpha, beta, False)
                if eval_val > max_eval: max_eval, best_move = eval_val, (move_type, move_data)
                alpha = max(alpha, eval_val)
                if beta <= alpha: break
            return max_eval, best_move
        else:
            min_eval = math.inf
            moves = self._get_possible_moves(p1_pos, p2_pos, p1_walls, h_walls, v_walls)
            if self.move_order_cache: moves.sort(key=lambda m: self.move_order_cache[0] == m, reverse=True)
            for move_type, move_data in moves:
                h_copy, v_copy = h_walls.copy(), v_walls.copy()
                if move_type == 'pawn':
                    eval_val, _ = self.minimax(move_data, p2_pos, p1_walls, p2_walls, h_copy, v_copy, depth - 1, alpha,
                                               beta, True)
                else:
                    wall_type, pos = move_data
                    if wall_type == 'h':
                        h_copy.add(pos)
                    else:
                        v_copy.add(pos)
                    p1_path = self.get_shortest_path(p1_pos, self.game.player1_goal_row, p2_pos, h_copy, v_copy)
                    p2_path = self.get_shortest_path(p2_pos, self.game.player2_goal_row, p1_pos, h_copy, v_copy)
                    if p1_path == math.inf or p2_path == math.inf:
                        eval_val = math.inf
                    else:
                        eval_val, _ = self.minimax(p1_pos, p2_pos, p1_walls - 1, p2_walls, h_copy, v_copy, depth - 1,
                                                   alpha, beta, True)
                if eval_val < min_eval: min_eval, best_move = eval_val, (move_type, move_data)
                beta = min(beta, eval_val)
                if beta <= alpha: break
            return min_eval, best_move

    def find_best_move(self, time_limit):
        is_p2_turn = self.player_number == 2

        def minimax_wrapper(result_container):
            start_time = time.time()
            p1_pos, p2_pos = self.game.player1_pos, self.game.player2_pos
            p1_walls, p2_walls = self.game.player1_walls, self.game.player2_walls
            h_walls, v_walls = self.game.horizontal_walls, self.game.vertical_walls
            best_move_overall = None
            final_score = 0

            for depth in range(1, 10):
                self.game.ai_search_depth = depth
                if time.time() - start_time > time_limit: break

                score_at_depth, best_move_at_depth = self.minimax(p1_pos, p2_pos, p1_walls, p2_walls, h_walls.copy(), v_walls.copy(),
                                                     depth, -math.inf, math.inf, is_p2_turn)

                if time.time() - start_time > time_limit:
                    if best_move_at_depth is not None: best_move_overall = best_move_at_depth
                    break

                best_move_overall = best_move_at_depth
                final_score = score_at_depth
                self.move_order_cache = [best_move_at_depth]

            if best_move_overall is None:
                my_pos = p2_pos if is_p2_turn else p1_pos
                op_pos = p1_pos if is_p2_turn else p2_pos
                possible_moves = self.game.calculate_valid_moves(my_pos, op_pos)
                if possible_moves: best_move_overall = ('pawn', possible_moves[0])

            result_container['move'] = best_move_overall
            result_container['score'] = final_score

        result = {}
        thread = threading.Thread(target=minimax_wrapper, args=(result,))
        thread.start()
        self.game.ai_thread_container[self.player_number] = {'thread': thread, 'result_dict': result}


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        pygame.display.set_caption('Quoridor')
        try:
            self.title_font = pygame.font.Font("EBGaramond-VariableFont_wght.ttf", 80)
            self.font = pygame.font.Font("EBGaramond-VariableFont_wght.ttf", 40)
            self.hud_font = pygame.font.Font("EBGaramond-VariableFont_wght.ttf", 32)
            self.small_hud_font = pygame.font.Font("EBGaramond-VariableFont_wght.ttf", 28)
            self.game_over_font = pygame.font.Font("EBGaramond-VariableFont_wght.ttf", 60)
        except FileNotFoundError:
            print("Font file not found, using default system font.")
            self.title_font = pygame.font.SysFont("georgia", 80)
            self.font = pygame.font.SysFont("segoeui", 40)
            self.hud_font = pygame.font.SysFont("segoeui", 32)
            self.small_hud_font = pygame.font.SysFont("segoeui", 28)
            self.game_over_font = pygame.font.SysFont("segoeui", 60)
        self.game_state = 'main_menu'
        self.game_mode = None
        self.pvp_button = pygame.Rect(150, 250, 300, 60)
        self.pvai_button = pygame.Rect(150, 350, 300, 60)
        self.aivai_button = pygame.Rect(150, 450, 300, 60)
        self.ai_player1 = AI(self, 1)
        self.ai_player2 = AI(self, 2)
        self.ai_is_thinking = False
        self.ai_thread_container = {}
        self.ai_start_time = 0
        self.ai_time_taken = 0
        self.ai_time_display_end_time = 0
        self.thinking_animation_angle = 0
        self.ai_search_depth = 0
        self.pulse_animation_timer = 0
        self.ghost_wall = None
        self.board_evaluation = 0.0
        board_pixel_height = (BOARD_SIZE * (SQUARE_SIZE - WALL_THICKNESS)) + ((BOARD_SIZE - 1) * WALL_THICKNESS)
        self.eval_bar_rect = pygame.Rect(
            BOARD_OFFSET_X - 45,  # Position it to the left of the board
            BOARD_OFFSET_Y,  # Align with the top of the board
            25,  # Width of the bar
            board_pixel_height  # Exact height of the board
        )
        self.animating = False
        self.animation_target_pos = None
        self.animating_pawn_pixels = [0, 0]
        self.animation_player = None
        self.reset_game()

    def reset_game(self):
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

    def draw_ghost_wall(self):
        if self.ghost_wall:
            wall_type, pos = self.ghost_wall
            c, r = pos

            # Create a semi-transparent surface for the ghost wall
            ghost_surface = pygame.Surface((SQUARE_SIZE * 2, SQUARE_SIZE * 2), pygame.SRCALPHA)

            # Check if this placement would be valid before drawing
            is_valid = self.is_valid_wall_placement(wall_type, pos) and (
                self.player1_walls if self.current_player == 1 else self.player2_walls) > 0

            # Green for valid, Red for invalid
            ghost_color = (65, 105, 225, 120) if is_valid else (220, 20, 60, 120)

            if wall_type == 'h':
                x = BOARD_OFFSET_X + c * SQUARE_SIZE
                y = BOARD_OFFSET_Y + r * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS)
                rect = pygame.Rect(x, y, SQUARE_SIZE * 2 - WALL_THICKNESS, WALL_THICKNESS)
            else:  # 'v'
                x = BOARD_OFFSET_X + c * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS)
                y = BOARD_OFFSET_Y + r * SQUARE_SIZE
                rect = pygame.Rect(x, y, WALL_THICKNESS, SQUARE_SIZE * 2 - WALL_THICKNESS)

            pygame.draw.rect(self.screen, ghost_color, rect, border_radius=3)

    def draw_pawns(self):
        # --- Draw Player 1 ---
        # If P1 is animating, draw it at its current pixel position
        if self.animating and self.animation_player == 1:
            pygame.draw.circle(self.screen, PLAYER1_COLOR, self.animating_pawn_pixels, SQUARE_SIZE / 3)
        else:  # Otherwise, draw it at its normal grid position
            p1_x = BOARD_OFFSET_X + self.player1_pos[0] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
            p1_y = BOARD_OFFSET_Y + self.player1_pos[1] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
            pygame.draw.circle(self.screen, PLAYER1_COLOR, (p1_x, p1_y), SQUARE_SIZE / 3)

        # --- Draw Player 2 ---
        # If P2 is animating, draw it at its current pixel position
        if self.animating and self.animation_player == 2:
            pygame.draw.circle(self.screen, PLAYER2_COLOR, self.animating_pawn_pixels, SQUARE_SIZE / 3)
        else:  # Otherwise, draw it at its normal grid position
            p2_x = BOARD_OFFSET_X + self.player2_pos[0] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
            p2_y = BOARD_OFFSET_Y + self.player2_pos[1] * SQUARE_SIZE + (SQUARE_SIZE - WALL_THICKNESS) / 2
            pygame.draw.circle(self.screen, PLAYER2_COLOR, (p2_x, p2_y), SQUARE_SIZE / 3)

    def draw_valid_moves(self):
        if not self.valid_moves:
            return

        # Create a pulsing effect for the size of the highlight rectangle
        # The value will smoothly oscillate between 0.0 and 1.0
        pulse = (math.sin(self.pulse_animation_timer * 0.05) + 1) / 2

        # This will make the inset oscillate between 4 and 8 pixels
        inset = 4 + pulse * 4

        for move in self.valid_moves:
            col, row = move
            x = BOARD_OFFSET_X + col * SQUARE_SIZE
            y = BOARD_OFFSET_Y + row * SQUARE_SIZE

            # Create a rectangle that shrinks and grows by changing its inset from the square's edge
            rect = pygame.Rect(
                x + inset,
                y + inset,
                (SQUARE_SIZE - WALL_THICKNESS) - (inset * 2),
                (SQUARE_SIZE - WALL_THICKNESS) - (inset * 2)
            )

            # The color is now a constant gold
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, rect, 3, border_radius=5)

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
            if self.is_wall_blocking(pawn_pos, next_pos): continue
            if next_pos == opponent_pos:
                jump_pos = (oc + dc, or_ + dr)
                if self.is_wall_blocking(opponent_pos, jump_pos) or not (
                        0 <= jump_pos[0] < BOARD_SIZE and 0 <= jump_pos[1] < BOARD_SIZE):
                    if dc == 0:
                        if not self.is_wall_blocking(opponent_pos,
                                                     (oc - 1, or_)) and 0 <= oc - 1 < BOARD_SIZE: moves.append(
                            (oc - 1, or_))
                        if not self.is_wall_blocking(opponent_pos,
                                                     (oc + 1, or_)) and 0 <= oc + 1 < BOARD_SIZE: moves.append(
                            (oc + 1, or_))
                    else:
                        if not self.is_wall_blocking(opponent_pos,
                                                     (oc, or_ - 1)) and 0 <= or_ - 1 < BOARD_SIZE: moves.append(
                            (oc, or_ - 1))
                        if not self.is_wall_blocking(opponent_pos,
                                                     (oc, or_ + 1)) and 0 <= or_ + 1 < BOARD_SIZE: moves.append(
                            (oc, or_ + 1))
                else:
                    moves.append(jump_pos)
                continue
            if 0 <= next_pos[0] < BOARD_SIZE and 0 <= next_pos[1] < BOARD_SIZE: moves.append(next_pos)
        return list(set(moves))

    def path_exists(self, start_pos, goal_row, opponent_pos):
        q = deque([start_pos])
        visited = {start_pos}
        while q:
            current_pos = q.popleft()
            if current_pos[1] == goal_row: return True
            for neighbor in self.calculate_valid_moves(current_pos, opponent_pos):
                if neighbor not in visited:
                    visited.add(neighbor);
                    q.append(neighbor)
        return False

    def is_wall_blocking(self, start_pos, end_pos):
        sc, sr = start_pos;
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
            c + 1, r) in self.vertical_walls: return False
            if (c, r) in self.horizontal_walls: return False
        return True


    def draw_hud(self):
        p1_hud_area = pygame.Rect(0, 0, SCREEN_WIDTH / 3, HUD_HEIGHT)
        p2_hud_area = pygame.Rect(SCREEN_WIDTH * 2 / 3, 0, SCREEN_WIDTH / 3, HUD_HEIGHT)

        # --- Determine AI thinking status ---
        is_p1_thinking = self.ai_is_thinking and self.current_player == 1 and self.game_mode == 'aivai'
        is_p2_thinking = self.ai_is_thinking and self.current_player == 2 and self.game_mode in ['pvai', 'aivai']

        # --- Player 1 HUD ---
        if is_p1_thinking:
            # Show "Thinking..." status for Player 1
            thinking_text = self.hud_font.render("Thinking...", True, PLAYER1_COLOR)
            thinking_rect = thinking_text.get_rect(center=(p1_hud_area.centerx, 30))
            self.screen.blit(thinking_text, thinking_rect)
            depth_text = self.small_hud_font.render(f"Depth: {self.ai_search_depth}", True, WHITE)
            depth_rect = depth_text.get_rect(center=(p1_hud_area.centerx, 70))
            self.screen.blit(depth_text, depth_rect)
            # Rotating arc animation for P1
            arc_center_y = thinking_rect.centery
            arc_center_x = p1_hud_area.left + 25
            arc_rect = pygame.Rect(arc_center_x - 12, arc_center_y - 12, 24, 24)
            start_angle = math.radians(self.thinking_animation_angle)
            end_angle = math.radians(self.thinking_animation_angle + 270)
            pygame.draw.arc(self.screen, PLAYER1_COLOR, arc_rect, start_angle, end_angle, 3)
            self.thinking_animation_angle = (self.thinking_animation_angle - 15) % 360
        else:
            # Show standard info for Player 1
            p1_title_text = self.hud_font.render("Player 1", True, PLAYER1_COLOR)
            p1_title_rect = p1_title_text.get_rect(center=(p1_hud_area.centerx, 30))
            self.screen.blit(p1_title_text, p1_title_rect)
            p1_wall_text = self.small_hud_font.render(f"Walls: {self.player1_walls}", True, WHITE)
            p1_wall_rect = p1_wall_text.get_rect(center=(p1_hud_area.centerx, 70))
            self.screen.blit(p1_wall_text, p1_wall_rect)

        # --- Player 2 HUD ---
        if is_p2_thinking:
            # Show "Thinking..." status for Player 2
            thinking_text = self.hud_font.render("Thinking...", True, PLAYER2_COLOR)
            thinking_rect = thinking_text.get_rect(center=(p2_hud_area.centerx, 30))
            self.screen.blit(thinking_text, thinking_rect)
            depth_text = self.small_hud_font.render(f"Depth: {self.ai_search_depth}", True, WHITE)
            depth_rect = depth_text.get_rect(center=(p2_hud_area.centerx, 70))
            self.screen.blit(depth_text, depth_rect)
            # Rotating arc animation for P2
            arc_center_y = thinking_rect.centery
            arc_center_x = p2_hud_area.right - 25
            arc_rect = pygame.Rect(arc_center_x - 12, arc_center_y - 12, 24, 24)
            start_angle = math.radians(self.thinking_animation_angle)
            end_angle = math.radians(self.thinking_animation_angle + 270)
            pygame.draw.arc(self.screen, PLAYER2_COLOR, arc_rect, start_angle, end_angle, 3)
            self.thinking_animation_angle = (self.thinking_animation_angle - 15) % 360
        else:
            # Show standard info for Player 2
            p2_title_text = self.hud_font.render("Player 2", True, PLAYER2_COLOR)
            p2_title_rect = p2_title_text.get_rect(center=(p2_hud_area.centerx, 30))
            self.screen.blit(p2_title_text, p2_title_rect)
            p2_wall_text = self.small_hud_font.render(f"Walls: {self.player2_walls}", True, WHITE)
            p2_wall_rect = p2_wall_text.get_rect(center=(p2_hud_area.centerx, 70))
            self.screen.blit(p2_wall_text, p2_wall_rect)

        # --- Turn Indicator (only shown when AI is not thinking) ---
        if not self.ai_is_thinking:
            if self.current_player == 1:
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, (p1_hud_area.left + 25, 30), 8)
            else:
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, (p2_hud_area.left + 25, 30), 8)

    def draw_error_message(self):
        current_time = pygame.time.get_ticks()
        if current_time < self.error_message_end_time:
            error_text = self.hud_font.render(self.error_message, True, ERROR_COLOR)
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH / 2, HUD_HEIGHT - 20))
            self.screen.blit(error_text, error_rect)

    def draw_game_over_screen(self):
        if self.game_state != 'game_over': return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
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

    def draw_evaluation_bar(self):
        border_rect = self.eval_bar_rect.inflate(4, 4)
        pygame.draw.rect(self.screen, BLACK, border_rect, border_radius=5)

        pygame.draw.rect(self.screen, (50, 50, 50), self.eval_bar_rect)

        squashed_eval = math.tanh(self.board_evaluation / 10.0)
        p1_height_ratio = (squashed_eval + 1) / 2.0
        p1_height = self.eval_bar_rect.height * p1_height_ratio

        p1_bar_rect = pygame.Rect(
            self.eval_bar_rect.left,
            self.eval_bar_rect.top,
            self.eval_bar_rect.width,
            p1_height
        )

        p2_bar_rect = pygame.Rect(
            self.eval_bar_rect.left,
            self.eval_bar_rect.top + p1_height,
            self.eval_bar_rect.width,
            self.eval_bar_rect.height - p1_height
        )

        pygame.draw.rect(self.screen, PLAYER1_COLOR, p1_bar_rect)
        pygame.draw.rect(self.screen, PLAYER2_COLOR, p2_bar_rect)

    def handle_click(self, mouse_pos):
        if self.ai_is_thinking: return
        if self.game_state == 'main_menu':
            if self.pvp_button.collidepoint(mouse_pos):
                self.game_mode, self.game_state = 'pvp', 'playing'; self.reset_game()
            elif self.pvai_button.collidepoint(mouse_pos):
                self.game_mode, self.game_state = 'pvai', 'playing'; self.reset_game()
            elif self.aivai_button.collidepoint(mouse_pos):
                self.game_mode, self.game_state = 'aivai', 'playing'; self.reset_game()
        elif self.game_state == 'playing':
            is_human_turn = self.game_mode == 'pvp' or (self.game_mode == 'pvai' and self.current_player == 1)
            if is_human_turn: self.handle_player_move(mouse_pos)
        elif self.game_state == 'game_over':
            self.game_state = 'main_menu'

    def handle_player_move(self, mouse_pos):
        self.selected_pawn = None;
        self.valid_moves = []
        clicked_square = self.get_square_from_pos(mouse_pos);
        clicked_wall = self.get_wall_from_pos(mouse_pos)
        current_pawn_pos = self.player1_pos if self.current_player == 1 else self.player2_pos
        opponent_pos = self.player2_pos if self.current_player == 1 else self.player1_pos
        current_valid_moves = self.calculate_valid_moves(current_pawn_pos, opponent_pos)
        if clicked_square:
            if clicked_square == current_pawn_pos:
                self.selected_pawn, self.valid_moves = current_pawn_pos, current_valid_moves
            elif clicked_square in current_valid_moves:
                self.execute_move(('pawn', clicked_square))
        elif clicked_wall:
            self.execute_move(('wall', clicked_wall))

    def execute_move(self, move):
        move_type, move_data = move
        if move_type == 'pawn':
            moving_player = self.current_player
            self.animating = True
            self.animation_player = moving_player
            self.animation_target_pos = move_data  # The target grid square (e.g., (4, 7))

            # Store the current pixel position of the pawn that is about to move
            start_pos = self.player1_pos if moving_player == 1 else self.player2_pos
            self.animating_pawn_pixels[0] = BOARD_OFFSET_X + start_pos[0] * SQUARE_SIZE + (
                        SQUARE_SIZE - WALL_THICKNESS) / 2
            self.animating_pawn_pixels[1] = BOARD_OFFSET_Y + start_pos[1] * SQUARE_SIZE + (
                        SQUARE_SIZE - WALL_THICKNESS) / 2

            # Update the logical position immediately, but the visual one will animate
            if moving_player == 1:
                self.player1_pos = move_data
            else:
                self.player2_pos = move_data
        elif move_type == 'wall':
            wall_type, pos = move_data
            if self.is_valid_wall_placement(wall_type, pos):
                if wall_type == 'h':
                    self.horizontal_walls.add(pos)
                else:
                    self.vertical_walls.add(pos)
                if self.path_exists(self.player1_pos, self.player1_goal_row, self.player2_pos) and self.path_exists(
                        self.player2_pos, self.player2_goal_row, self.player1_pos):
                    if self.current_player == 1:
                        self.player1_walls -= 1
                    else:
                        self.player2_walls -= 1
                    self.current_player = 3 - self.current_player
                else:
                    self.error_message = "Wall must not block all paths!";
                    self.error_message_end_time = pygame.time.get_ticks() + 3000
                    if wall_type == 'h':
                        self.horizontal_walls.remove(pos)
                    else:
                        self.vertical_walls.remove(pos)

    def run(self):
        running = True
        while running:
            self.pulse_animation_timer += 1
            if self.animating:
                # Calculate the destination pixel position
                target_x = BOARD_OFFSET_X + self.animation_target_pos[0] * SQUARE_SIZE + (
                            SQUARE_SIZE - WALL_THICKNESS) / 2
                target_y = BOARD_OFFSET_Y + self.animation_target_pos[1] * SQUARE_SIZE + (
                            SQUARE_SIZE - WALL_THICKNESS) / 2

                # --- NEW VECTOR-BASED MOVEMENT ---
                # Calculate the vector from current position to target
                dx = target_x - self.animating_pawn_pixels[0]
                dy = target_y - self.animating_pawn_pixels[1]
                distance = math.hypot(dx, dy)

                # Define a constant speed in pixels per frame
                animation_speed = 15

                # If we are close enough to the target, snap to it and end the animation
                if distance < animation_speed:
                    self.animating_pawn_pixels[0] = target_x
                    self.animating_pawn_pixels[1] = target_y
                    self.animating = False  # Stop the animation

                    # --- Logic that happens *after* a move is complete ---
                    pawn_pos = self.player1_pos if self.animation_player == 1 else self.player2_pos
                    goal_row = self.player1_goal_row if self.animation_player == 1 else self.player2_goal_row
                    if pawn_pos[1] == goal_row:
                        self.winner, self.game_state = self.animation_player, 'game_over'
                    else:
                        self.current_player = 3 - self.current_player
                else:
                    # Move by a fixed amount (speed) along the vector
                    self.animating_pawn_pixels[0] += (dx / distance) * animation_speed
                    self.animating_pawn_pixels[1] += (dy / distance) * animation_speed
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.animating:
                        self.handle_click(pygame.mouse.get_pos())

            is_ai_turn_now = not self.ai_is_thinking and self.game_state == 'playing' and not self.animating and (
                    (self.game_mode == 'pvai' and self.current_player == 2) or
                    (self.game_mode == 'aivai')
            )

            if is_ai_turn_now:
                self.ai_is_thinking = True
                self.ai_start_time = time.time()
                ai_to_move = self.ai_player1 if self.current_player == 1 else self.ai_player2
                ai_to_move.find_best_move(time_limit=3)

            if self.ai_is_thinking:
                thread_info = self.ai_thread_container.get(self.current_player)
                if thread_info and not thread_info['thread'].is_alive():
                    self.ai_is_thinking = False
                    self.ai_time_taken = time.time() - self.ai_start_time
                    self.ai_time_display_end_time = time.time() + 2
                    result_dict = thread_info['result_dict']
                    move = result_dict.get('move')
                    score = result_dict.get('score')

                    if score is not None:
                        self.board_evaluation = score

                    if move:
                        self.execute_move(move)
                    else:
                        my_pos = self.player1_pos if self.current_player == 1 else self.player2_pos
                        op_pos = self.player2_pos if self.current_player == 1 else self.player1_pos
                        pawn_moves = self.calculate_valid_moves(my_pos, op_pos)
                        if pawn_moves: self.execute_move(('pawn', pawn_moves[0]))

            is_human_turn = not self.ai_is_thinking and not self.animating and (
                    self.game_mode == 'pvp' or (self.game_mode == 'pvai' and self.current_player == 1)
            )
            if is_human_turn:
                mouse_pos = pygame.mouse.get_pos()
                # Check for a square click first to avoid overlaps
                clicked_square = self.get_square_from_pos(mouse_pos)
                if not clicked_square:
                    self.ghost_wall = self.get_wall_from_pos(mouse_pos)
                else:
                    self.ghost_wall = None
            else:
                self.ghost_wall = None

            self.screen.fill(BROWN)
            if self.game_state == 'main_menu':
                self.draw_main_menu()
            elif self.game_state == 'playing' or self.game_state == 'game_over':
                self.draw_board()
                self.draw_walls()
                if self.game_state == 'playing': self.draw_valid_moves()
                self.draw_ghost_wall()
                self.draw_pawns()
                self.draw_hud()
                self.draw_error_message()
                self.draw_evaluation_bar()
                if self.game_state == 'game_over': self.draw_game_over_screen()
                self.draw_evaluation_bar()

            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    game = Game()
    game.run()