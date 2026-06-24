import time
import random  # <--- Добавили для случайности в дебютах
import berserk
import chess

# ================= 1. УМНЫЙ ШАХМАТНЫЙ ДВИЖОК =================

def evaluate_board(board):
    """ Оценка позиции на доске с учетом материала и геометрии """
    piece_values = {
        chess.PAWN: 1.0,
        chess.KNIGHT: 3.0,
        chess.BISHOP: 3.0,
        chess.ROOK: 5.0,
        chess.QUEEN: 9.0,
        chess.KING: 0.0
    }
    
    score = 0.0
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = piece_values[piece.piece_type]
            
            # --- ПОЗИЦИОННАЯ ЛОГИКА (ЦЕНТР И РАЗВИТИЕ) ---
            row = chess.square_rank(square)  # 0-7
            col = chess.square_file(square)  # 0-7
            
            dist_from_center = abs(3.5 - row) + abs(3.5 - col)
            center_bonus = (8.0 - dist_from_center) * 0.05
            
            if piece.piece_type == chess.PAWN:
                pawn_bonus = row * 0.1 if piece.color == chess.WHITE else (7 - row) * 0.1
                val += (center_bonus + pawn_bonus)
            elif piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                val += center_bonus
                
            if piece.color == chess.WHITE:
                score += val
            else:
                score -= val
                
    return score

def minimax(board, depth, alpha, beta, is_maximizing):
    """ Минимакс с альфа-бета отсечением """
    if board.is_game_over():
        outcome = board.outcome()
        if outcome.winner == chess.WHITE:
            return 10000.0 + depth
        elif outcome.winner == chess.BLACK:
            return -10000.0 - depth
        return 0.0

    if depth == 0:
        return evaluate_board(board)

    ordered_moves = sorted(board.legal_moves, key=lambda m: board.is_capture(m), reverse=True)

    if is_maximizing:
        best = -float('inf')
        for move in ordered_moves:
            board.push(move)
            val = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in ordered_moves:
            board.push(move)
            val = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

def find_best_move(board, depth):
    """ Ищет лучший ход с защитой от повторяющихся партий """
    my_color = board.turn
    
    # Хитрый трюк: превращаем ходы в список и перемешиваем их
    legal_moves_list = list(board.legal_moves)
    random.shuffle(legal_moves_list)
    
    # Стабильная сортировка в Python сохранит случайный порядок среди ходов с одинаковым приоритетом (например, среди не-взятий)
    ordered_moves = sorted(legal_moves_list, key=lambda m: board.is_capture(m), reverse=True)
    
    best_move = None
    alpha = -float('inf')
    beta = float('inf')

    if my_color == chess.WHITE:
        best_score = -float('inf')
        for move in ordered_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
    else:
        best_score = float('inf')
        for move in ordered_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            
    return best_move

# ================= 2. ПОДКЛЮЧЕНИЕ И ИГРОВОЙ ЦИКЛ =================
TOKEN = "lip_XG5jv7YWcOFKO1Sg6RRG"

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session)

my_username = client.account.get()['username']
print(f"Я бот {my_username}")
print("Мой бот запущен и готов побеждать!")

while True:
    try:
        for event in client.bots.stream_incoming_events():
            if event.get('type') == 'challenge':
                challenge_id = event.get('challenge', {}).get('id')
                if challenge_id:
                    client.bots.accept_challenge(challenge_id)
                    print(f"Вызов {challenge_id} принят!")

            if event.get('type') == 'gameStart':
                game_id = event.get('game', {}).get('id')
                print(f"Игра {game_id} началась!")
                board = chess.Board()
                moves = []
                my_color = None

                try:
                    for state in client.bots.stream_game_state(game_id):
                        state_type = state.get('type')
                        game_data = None

                        if state_type == 'gameFull':
                            white_id = state.get('white', {}).get('id', '')
                            black_id = state.get('black', {}).get('id', '')
                            if white_id.lower() == my_username.lower():
                                my_color = chess.WHITE
                            elif black_id.lower() == my_username.lower():
                                my_color = chess.BLACK
                            
                            print(f"Я играю {'белыми' if my_color == chess.WHITE else 'чёрными'}")
                            game_data = state.get('state', {})
                        
                        elif state_type == 'gameState':
                            game_data = state

                        if game_data:
                            raw_moves = game_data.get('moves', '')
                            all_moves = raw_moves.split() if raw_moves else []
                            
                            while len(moves) < len(all_moves):
                                board.push_uci(all_moves[len(moves)])
                                moves.append(all_moves[len(moves)-1])

                            status = game_data.get('status')
                            if status in ['mate', 'resign', 'draw', 'stalemate', 'timeout', 'outoftime', 'aborted']:
                                print(f"Игра {game_id} завершена (статус: {status})")
                                break

                        if my_color is not None and board.turn == my_color and not board.is_game_over():
                            print("Мой ход! Думаю...")
                            move = find_best_move(board, depth=3)
                            if move:
                                time.sleep(0.1)
                                client.bots.make_move(game_id, move.uci())
                                print(f"Сделал ход: {move.uci()}")

                except Exception as e:
                    print(f"Ошибка в игре {game_id}: {e}")
                    import traceback
                    traceback.print_exc()

                print("Выход из игры, жду новые вызовы...")

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        time.sleep(5)
