import time
import random
import threading
import json
import os
import traceback
import berserk
import chess
import chess.polyglot

# ================= 1. РАСШИРЕННАЯ ДЕБЮТНАЯ КНИГА ОСТРЫХ ЛИНИЙ =================

OPENING_BOOK = {
    "": ["e2e4", "d2d4", "g1f3", "c4c4"],
    "e2e4 e7e5": ["g1f3"],
    "e2e4 e7e5 g1f3": ["b8c6"],
    "e2e4 e7e5 g1f3 b8c6": ["b1b5", "d2d4", "b1c4"],
    "e2e4 e7e5 g1f3 b8c6 b1c4": ["f8c5"],
    "e2e4 e7e5 g1f3 b8c6 b1c4 f8c5": ["b2b4", "c2c3"], 
    "e2e4 e7e5 g1f3 b8c6 b1c4 f8c5 b2b4 c5b4 c2c3": ["b4a5", "b4c5"],
    "e2e4 e7e5 g1f3 b8c6 d2d4": ["e5d4"],
    "e2e4 e7e5 g1f3 b8c6 d2d4 e5d4": ["f3d4"],
    "e2e4 e7e5 g1f3 b8c6 d2d4 e5d4 f3d4 g8f6": ["b1c3", "d4c6"],
    "e2e4 c7c5": ["g1f3", "b1c3"],
    "e2e4 c7c5 g1f3": ["d7d6", "e7e6", "b8c6"],
    "e2e4 c7c5 g1f3 d7d6": ["d2d4"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4": ["f3d4"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6": ["b1c3"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6": ["c1g5", "f2f4", "f2f3"],
    "e2e4 e7e6": ["d2d4"],
    "e2e4 e7e6 d2d4 d5": ["b1c3", "e4e5"],
    "e2e4 c7c6": ["d2d4"],
    "e2e4 c7c6 d2d4 d5": ["b1c3", "e4e5"],
    "d2d4 d7d5": ["c4c4"],
    "d2d4 d7d5 c4c4": ["e7e6", "c7c6", "d5c4"],
    "d2d4 g8f6": ["c4c4"],
    "d2d4 g8f6 c4c4": ["g7g6", "e7e6"],
    "e2e4": ["c7c5", "e7e5", "c7c6"],
    "d2d4": ["g8f6", "d7d5"],
    "g1f3": ["d7d5", "g8f6"],
    "c4c4": ["e7e5", "c7c5"]
}

# ================= 2. ПОЗИЦИОННЫЕ МАТРИЦЫ (PST) ДЛЯ 1600 ELO =================

PAWN_PST = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_PST = [
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0
]

QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10,-5,  -5,-10,-10,-20
]

KING_MIDDLEGAME_PST = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

KING_ENDGAME_PST = [
    -50,-30,-30,-30,-30,-30,-30,-50,
    -30,-10,  0,  0,  0,  0,-10,-30,
    -30,  0, 20, 30, 30, 20,  0,-30,
    -30,  0, 30, 40, 40, 30,  0,-30,
    -30,  0, 30, 40, 40, 30,  0,-30,
    -30,  0, 20, 30, 30, 20,  0,-30,
    -30,-10,  0,  0,  0,  0,-10,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
]

# ================= 3. ЧЕРНЫЙ СПИСОК ОШИБОК =================

MEMORY_FILE = "bot_memory.json"
memory_lock = threading.Lock()
bad_moves_db = {}

def load_memory():
    global bad_moves_db
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                bad_moves_db = json.load(f)
            print(f"🧠 База данных ошибок загружена. Записей: {len(bad_moves_db)}")
        except Exception:
            bad_moves_db = {}

def save_bad_move(fen, move_uci):
    global bad_moves_db
    with memory_lock:
        short_fen = " ".join(fen.split()[:3])
        if short_fen not in bad_moves_db:
            bad_moves_db[short_fen] = []
        if move_uci not in bad_moves_db[short_fen]:
            bad_moves_db[short_fen].append(move_uci)
            print(f"💾 Ошибка зафиксирована! Ход {move_uci} забанен для позиции: {short_fen}")
            try:
                with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(bad_moves_db, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

# ================= 4. ФУНКЦИЯ ОЦЕНКИ С ОПТИМИЗАЦИЕЙ =================

def evaluate_board(board):
    if board.is_checkmate():
        return -99999.0 if board.turn == chess.WHITE else 99999.0
    if board.is_stalemate() or board.is_insufficient_material():
        return 0.0

    piece_values = {
        chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
        chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000
    }
    
    num_heavy_pieces = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK)) + \
                       len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
    is_endgame = num_heavy_pieces <= 2

    white_king_sq = board.king(chess.WHITE)
    black_king_sq = board.king(chess.BLACK)

    score = 0
    
    for square, piece in board.piece_map().items():
        val = piece_values[piece.piece_type]
        idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
        
        if not board.chess960:
            if piece.piece_type == chess.PAWN: val += PAWN_PST[idx]
            elif piece.piece_type == chess.KNIGHT: val += KNIGHT_PST[idx]
            elif piece.piece_type == chess.BISHOP: val += BISHOP_PST[idx]
            elif piece.piece_type == chess.ROOK: val += ROOK_PST[idx]      # Новое!
            elif piece.piece_type == chess.QUEEN: val += QUEEN_PST[idx]    # Новое!
            elif piece.piece_type == chess.KING:
                val += KING_ENDGAME_PST[idx] if is_endgame else KING_MIDDLEGAME_PST[idx]
        
        # Охота на короля в миттельшпиле
        if not is_endgame and piece.piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            enemy_king = black_king_sq if piece.color == chess.WHITE else white_king_sq
            if enemy_king is not None:
                dist = chess.square_distance(square, enemy_king)
                if dist <= 3:
                    val += (4 - dist) * 15

        if piece.color == chess.WHITE:
            score += val
        else:
            score -= val

    # Мобильность фигур (активность на доске)
    mobility = board.legal_moves.count()
    if board.turn == chess.WHITE:
        score += mobility * 2
    else:
        score -= mobility * 2
                
    return score / 100.0

# ================= 5. СОРТИРОВКА ХОДОВ (MVV-LVA) =================

def score_move(board, move):
    if board.is_capture(move):
        attacker = board.piece_at(move.from_square)
        target = board.piece_at(move.to_square)
        attacker_val = attacker.piece_type if attacker else 1
        target_val = target.piece_type if target else 1
        return 1000 + (target_val * 10 - attacker_val)
    if board.gives_check(move):
        return 500
    return 0

# ================= 6. ПОИСК ЗАТИШЬЯ (QUIESCENCE) =================

def quiescence(board, alpha, beta):
    stand_pat = evaluate_board(board)
    if board.turn == chess.WHITE:
        if stand_pat >= beta: return beta
        if alpha < stand_pat: alpha = stand_pat
        
        capture_moves = [m for m in board.legal_moves if board.is_capture(m)]
        ordered_captures = sorted(capture_moves, key=lambda m: score_move(board, m), reverse=True)
        
        for move in ordered_captures:
            board.push(move)
            score = quiescence(board, alpha, beta)
            board.pop()
            if score >= beta: return beta
            if score > alpha: alpha = score
        return alpha
    else:
        if stand_pat <= alpha: return alpha
        if beta > stand_pat: beta = stand_pat
        
        capture_moves = [m for m in board.legal_moves if board.is_capture(m)]
        ordered_captures = sorted(capture_moves, key=lambda m: score_move(board, m), reverse=True)
        
        for move in ordered_captures:
            board.push(move)
            score = quiescence(board, alpha, beta)
            board.pop()
            if score <= alpha: return alpha
            if score < beta: beta = score
        return beta

# ================= 7. МИНИМАКС ПОИСК =================

def minimax(board, depth, alpha, beta, is_maximizing):
    if board.is_repetition(3): 
        return 0.0
    if board.is_game_over() or depth == 0:
        return quiescence(board, alpha, beta)

    ordered_moves = sorted(board.legal_moves, key=lambda m: score_move(board, m), reverse=True)

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

# ================= 8. СТРАТЕГИЧЕСКИЙ ВЫБОР ХОДА =================

def find_best_move(board, depth=3):
    my_color = board.turn
    
    # 1. Polyglot книга
    if os.path.exists("book.bin") and not board.chess960:
        try:
            with chess.polyglot.open_reader("book.bin") as reader:
                entries = list(reader.find_all(board))
                if entries:
                    best_entry = max(entries, key=lambda e: e.weight)
                    print(f"📖 [Polyglot] Идеальный ход: {best_entry.move()}")
                    return best_entry.move(), evaluate_board(board)
        except Exception as e:
            print(f"⚠️ Ошибка Polyglot: {e}")

    # 2. Текстовая книга дебютов
    if not board.chess960:
        move_history = " ".join([m.uci() for m in board.move_stack])
        if move_history in OPENING_BOOK:
            book_choices = OPENING_BOOK[move_history]
            legal_book = [chess.Move.from_uci(m) for m in book_choices if chess.Move.from_uci(m) in board.legal_moves]
            if legal_book:
                chosen_book_move = random.choice(legal_book)
                print(f"📖 [Книга Дебютов] Вариант: {chosen_book_move.uci()}")
                return chosen_book_move, evaluate_board(board)

    # 3. Расчет движка
    short_fen = " ".join(board.fen().split()[:3])
    legal_moves_list = list(board.legal_moves)
    random.shuffle(legal_moves_list)
    ordered_moves = sorted(legal_moves_list, key=lambda m: score_move(board, m), reverse=True)
    
    best_move = None
    alpha, beta = -float('inf'), float('inf')
    known_bad_moves = bad_moves_db.get(short_fen, [])

    if my_color == chess.WHITE:
        best_score = -float('inf')
        for move in ordered_moves:
            move_uci = move.uci()
            board.push(move)
            
            if move_uci in known_bad_moves: 
                score = -9000.0
            else: 
                score = minimax(board, depth - 1, alpha, beta, False)
                
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
    else:
        best_score = float('inf')
        for move in ordered_moves:
            move_uci = move.uci()
            board.push(move)
            
            if move_uci in known_bad_moves: 
                score = 9000.0
            else: 
                score = minimax(board, depth - 1, alpha, beta, True)
                
            board.pop()
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            
    if not best_move and legal_moves_list:
        best_move = random.choice(legal_moves_list)
        
    return best_move, best_score

# ================= 9. ЦИКЛ ВЗАИМОДЕЙСТВИЯ С LICHESS =================

TOKEN = os.environ.get("LICHESS_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: Переменная LICHESS_TOKEN не найдена!")
    exit(1)

def run_chess_bot():
    load_memory()
    session = berserk.TokenSession(TOKEN)
    client = berserk.Client(session)
    
    my_username = client.account.get()['username']
    my_id = client.account.get()['id']
    print(f"🚀 Het-AI в боевой готовности! Бот запущен как: @{my_username}")

    active_games = set()
    MAX_CONCURRENT_GAMES = 2

    def auto_challenger():
        while True:
            try:
                if len(active_games) < MAX_CONCURRENT_GAMES:
                    online_bots = [b['id'] for b in client.bots.get_online_bots() if b.get('id') != my_id]
                    if online_bots:
                        target = random.choice(online_bots)
                        print(f"⚔️ Кидаем вызов: @{target}")
                        client.challenges.create(username=target, rated=True, clock_limit=180, clock_increment=2, variant='standard')
                time.sleep(45)
            except Exception as e:
                time.sleep(60 if "429" in str(e) else 20)

    threading.Thread(target=auto_challenger, daemon=True).start()

    def handle_game(game_id):
        try:
            board = None
            my_color = None
            moves_count = 0
            my_history = []
            
            greetings = [
                "Привет! Поиграем? Удачи! 🤖",
                "Приветствую! Пусть победит сильнейший! ⚔️",
                "Здравствуй, человек. Het-AI готов к бою! 🚀",
                "Привет! Надеюсь, игра будет интересной. Нападай! 🔥"
            ]
            goodbyes_win = [
                "Отличная игра! Спасибо за партию. 🤝",
                "Шах и мат. Было круто, спасибо! 👑",
                "Хорошо сыграно! Удачи в следующих играх!"
            ]
            goodbyes_lose = [
                "Ух, это было мощно. Поздравляю с победой! 👏",
                "Отличный маневр! Меня надо подкрутить... 🛠️",
                "Хорошая игра! Спасибо за урок."
            ]

            for state in client.bots.stream_game_state(game_id):
                if state.get('type') == 'gameFull':
                    initial_fen = state.get('initialFen', chess.STARTING_FEN)
                    if initial_fen == 'startpos':
                        initial_fen = chess.STARTING_FEN
                    
                    board = chess.Board(initial_fen)
                    white_id = state.get('white', {}).get('id', '')
                    my_color = chess.WHITE if white_id.lower() == my_username.lower() else chess.BLACK
                    
                    try:
                        client.bots.post_message(game_id, random.choice(greetings))
                    except Exception:
                        pass
                        
                    game_state = state.get('state', {})
                else:
                    game_state = state

                raw_moves = game_state.get('moves', '').split()
                while moves_count < len(raw_moves):
                    board.push_uci(raw_moves[moves_count])
                    moves_count += 1

                # УМНЫЙ И БЕЗОПАСНЫЙ ТАЙМ-МЕНЕДЖМЕНТ
                my_time_key = 'wtime' if my_color == chess.WHITE else 'btime'
                raw_time = game_state.get(my_time_key)
                
                if hasattr(raw_time, 'total_seconds'):
                    available_time = raw_time.total_seconds()
                elif raw_time is not None:
                    available_time = float(raw_time) / 1000.0
                else:
                    available_time = 180.0
                
                # ДИНАМИЧЕСКАЯ ГЛУБИНА С ФОРСАЖЕМ ДЛЯ БЛИЦА И РАПИДА
                if available_time < 15: 
                    current_depth = 1  
                elif available_time < 45: 
                    current_depth = 2
                elif available_time < 90: 
                    current_depth = 3   # В пуле и в эндшпиле блица играем быстро
                else: 
                    current_depth = 4   # Когда времени много (Блиц/Рапид), считаем на ход глубже!

                status = game_state.get('status')
                if status in ['mate', 'resign', 'draw', 'timeout', 'stalemate', 'outoftime']:
                    try:
                        winner = game_state.get('winner')
                        if winner:
                            if (winner == 'white' and my_color == chess.WHITE) or (winner == 'black' and my_color == chess.BLACK):
                                client.bots.post_message(game_id, random.choice(goodbyes_win))
                            else:
                                client.bots.post_message(game_id, random.choice(goodbyes_lose))
                        else:
                            client.bots.post_message(game_id, "Ничья! Отличный баланс сил. Спасибо за игру! 🤝")
                    except Exception:
                        pass

                    if game_state.get('winner') and my_history:
                        winner = game_state['winner']
                        if (winner == 'white' and my_color == chess.BLACK) or (winner == 'black' and my_color == chess.WHITE):
                            save_bad_move(my_history[-1][0], my_history[-1][1])
                    break

                if board.turn == my_color and not board.is_game_over():
                    current_fen = board.fen()
                    move, score = find_best_move(board, depth=current_depth)
                    if move:
                        move_uci = move.uci()
                        print(f"🎯 [{game_id}] Ход: {move_uci} (Оценка: {score:+.2f} | Глубина: {current_depth})")
                        try:
                            client.bots.make_move(game_id, move_uci)
                            my_history.append((current_fen, move_uci))
                        except Exception as e:
                            print(f"❌ Ход сорвался: {e}")
        except Exception as e:
            traceback.print_exc()
        finally:
            active_games.discard(game_id)

    while True:
        try:
            for event in client.bots.stream_incoming_events():
                event_type = event.get('type')
                if event_type == 'challenge':
                    c_id = event['challenge']['id']
                    if len(active_games) < MAX_CONCURRENT_GAMES:
                        client.bots.accept_challenge(c_id)
                    else:
                        client.bots.decline_challenge(c_id, reason='later')
                elif event_type == 'gameStart':
                    g_id = event['game']['id']
                    if g_id not in active_games:
                        active_games.add(g_id)
                        threading.Thread(target=handle_game, args=(g_id,), daemon=True).start()
        except Exception as e:
            time.sleep(60 if "429" in str(e) else 5)

if __name__ == '__main__':
    run_chess_bot()
