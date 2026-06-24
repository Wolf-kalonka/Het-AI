import time
import berserk
import chess

# ================= 1. ШАХМАТНЫЙ ДВИЖОК =================
def evaluate_board(board):
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0
    }
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            if piece.color == chess.WHITE:
                score += piece_values[piece.piece_type]
            else:
                score -= piece_values[piece.piece_type]
    return score

def minimax(board, depth, is_maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    if is_maximizing:
        best = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            val = minimax(board, depth-1, False)
            board.pop()
            best = max(best, val)
        return best
    else:
        best = float('inf')
        for move in board.legal_moves:
            board.push(move)
            val = minimax(board, depth-1, True)
            board.pop()
            best = min(best, val)
        return best

def find_best_move(board, depth):
    best_move = None
    best_score = -float('inf')
    for move in board.legal_moves:
        board.push(move)
        score = minimax(board, depth-1, False)
        board.pop()
        if score > best_score:
            best_score = score
            best_move = move
    return best_move

# ================= 2. ПОДКЛЮЧЕНИЕ И ИГРОВОЙ ЦИКЛ =================
TOKEN = "lip_XG5jv7YWcOFKO1Sg6RRG"

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session)

my_username = client.account.get()['username']
print(f"Я бот {my_username}")
print("Мой бот запущен и ждет игр!")

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

                        # Извлекаем актуальные ходы и статус в зависимости от типа события
                        if state_type == 'gameFull':
                            white_id = state.get('white', {}).get('id', '')
                            black_id = state.get('black', {}).get('id', '')
                            if white_id.lower() == my_username.lower():
                                my_color = chess.WHITE
                            elif black_id.lower() == my_username.lower():
                                my_color = chess.BLACK
                            
                            print(f"Я играю {'белыми' if my_color == chess.WHITE else 'чёрными'}")
                            game_data = state.get('state', {}) # Ходы в gameFull лежат внутри 'state'
                        
                        elif state_type == 'gameState':
                            game_data = state

                        # Обновляем доску (работает и для gameFull, и для gameState)
                        if game_data:
                            raw_moves = game_data.get('moves', '')
                            all_moves = raw_moves.split() if raw_moves else []
                            
                            # Накатываем новые ходы
                            while len(moves) < len(all_moves):
                                board.push_uci(all_moves[len(moves)])
                                moves.append(all_moves[len(moves)-1])

                            # Проверяем статус завершения игры
                            status = game_data.get('status')
                            if status in ['mate', 'resign', 'draw', 'stalemate', 'timeout', 'outoftime', 'aborted']:
                                print(f"Игра {game_id} завершена (статус: {status})")
                                break

                        # Делаем ход (теперь срабатывает СРАЗУ на gameFull, если мы белые)
                        if my_color is not None and board.turn == my_color and not board.is_game_over():
                            print("Мой ход! Думаю...")
                            move = find_best_move(board, depth=2)
                            if move:
                                time.sleep(0.2)  # Небольшая пауза для стабильности
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