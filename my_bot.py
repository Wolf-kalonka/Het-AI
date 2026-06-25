import time
import random
import threading
import json
import os
import berserk
import chess

# ================= 1. ДЕБЮТНЫЕ КНИГИ (OPENING BOOKS) =================
# Книга работает по истории ходов в формате UCI. Если позиция знакома, бот ходит мгновенно.

OPENING_BOOK = {
    # --- БЕЛЫЕ: Стартовые ходы ---
    "": ["e2e4", "d2d4", "g1f3", "c2c4"],
    
    # Реакции на e4 e5 (Испанская / Итальянская / Гамбит)
    "e2e4 e7e5": ["g1f3"],
    "e2e4 e7e5 g1f3": ["b8c6"],
    "e2e4 e7e5 g1f3 b8c6": ["b1b5", "b1c4", "d2d4"], # Испанская, Итальянская или Шотландская
    
    # Реакции на Сицилианку (c7c5)
    "e2e4 c7c5": ["g1f3", "b1c3"],
    "e2e4 c7c5 g1f3": ["d7d6", "e7e6", "b8c6"],
    "e2e4 c7c5 g1f3 d7d6": ["d2d4"],
    
    # Реакции на Ферзевый гамбит
    "d2d4 d7d5": ["c2c4"],
    "d2d4 d7d5 c2c4": ["e7e6", "c7c6"], # Отказанный или Славянская
    
    # --- ЧЕРНЫЕ: Ответы на первые ходы белых ---
    "e2e4": ["c7c5", "e7e5", "e7e6", "c7c6"], # Сицилианка, Открытый, Французская, Каро-Канн
    "d2d4": ["d7d5", "g8f6"],
    "g1f3": ["d7d5", "g8f6"],
    "c2c4": ["e7e5", "c7c5"],
    
    # Линии за черных в Сицилианке
    "e2e4 c7c5 g1f3": ["d7d6", "b8c6"],
    "e2e4 c7c5 g1f3 d7d6 d2d4": ["c5d4"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4": ["g8f6"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3": ["a7a6", "g7g6"], # Найддорф или Дракон
}

# ================= 2. ПОЗИЦИОННЫЕ МАТРИЦЫ ДЛЯ УСИЛЕНИЯ ИГРЫ =================
# Бонусы за нахождение фигур на правильных клетках (вид с точки зрения Белых)

PAWN_PST = [
    0,  0,  0,  0,  0,  0,  0,  0,
    5,  5,  5,  5,  5,  5,  5,  5,
    1,  1,  2,  3,  3,  2,  1,  1,
    0,  0,  2,  4,  4,  2,  0,  0,
    0,  0,  1,  4,  4,  1,  0,  0,
    1, -1, -2,  0,  0, -2, -1,  1,
    1,  2,  2, -3, -3,  2,  2,  1,
    0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_PST = [
    -5, -4, -3, -3, -3, -3, -4, -5,
    -4, -2,  0,  0,  0,  0, -2, -4,
    -3,  0,  1,  2,  2,  1,  0, -3,
    -3,  1,  2,  3,  3,  2,  1, -3,
    -3,  0,  2,  3,  3,  2,  0, -3,
    -3,  1,  1,  2,  2,  1,  1, -3,
    -4, -2,  0,  1,  1,  0, -2, -4,
    -5, -4, -3, -3, -3, -3, -4, -5
]

BISHOP_PST = [
    -2, -1, -1, -1, -1, -1, -1, -2,
    -1,  0,  0,  0,  0,  0,  0, -1,
    -1,  0,  1,  2,  2,  1,  0, -1,
    -1,  1,  1,  2,  2,  1,  1, -1,
    -1,  0,  2,  2,  2,  2,  0, -1,
    -1,  2,  2,  1,  1,  2,  2, -1,
    -1,  1,  0,  0,  0,  0,  1, -1,
    -2, -1, -1, -1, -1, -1, -1, -2
]

KING_PST = [
    -3, -4, -4, -5, -5, -4, -4, -3,
    -3, -4, -4, -5, -5, -4, -4, -3,
    -3, -4, -4, -5, -5, -4, -4, -3,
    -3, -4, -4, -5, -5, -4, -4, -3,
    -2, -3, -3, -4, -4, -3, -3, -2,
    -1, -2, -2, -2, -2, -2, -2, -1,
     2,  2,  0,  0,  0,  0,  2,  2,
     2,  3,  1,  0,  0,  1,  3,  2
]

# ================= 3. ДВИЖОК И ПАМЯТЬ =================

MEMORY_FILE = "bot_memory.json"
memory_lock = threading.Lock()
bad_moves_db = {}

def load_memory():
    global bad_moves_db
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                bad_moves_db = json.load(f)
            print(f"🧠 Память загружена! Найдено позиций с ошибками: {len(bad_moves_db)}")
        except Exception as e:
            print(f"⚠️ Ошибка чтения памяти: {e}.")
            bad_moves_db = {}
    else:
        bad_moves_db = {}

def save_bad_move(fen, move_uci):
    global bad_moves_db
    with memory_lock:
        # Для Фишера важна структура рокировок, берем первые 3 части FEN
        short_fen = " ".join(fen.split()[:3])
        if short_fen not in bad_moves_db:
            bad_moves_db[short_fen] = []
        if move_uci not in bad_moves_db[short_fen]:
            bad_moves_db[short_fen].append(move_uci)
            print(f"💾 Ошибка {move_uci} сохранена для: {short_fen}")
            try:
                with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(bad_moves_db, f, indent=4, ensure_ascii=False)
            except Exception: pass

def evaluate_board(board):
    """ Оценка доски с учетом материала и позиционных таблиц (PST) """
    piece_values = {
        chess.PAWN: 1.0, chess.KNIGHT: 3.1, chess.BISHOP: 3.25,
        chess.ROOK: 5.0, chess.QUEEN: 9.0, chess.KING: 0.0
    }
    
    score = 0.0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = piece_values[piece.piece_type]
            
            # Индекс для матриц (для черных переворачиваем доску)
            idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
            
            # Добавляем позиционные бонусы (только для стандартных шахмат)
            if not board.chess960:
                if piece.piece_type == chess.PAWN: val += PAWN_PST[idx] * 0.1
                elif piece.piece_type == chess.KNIGHT: val += KNIGHT_PST[idx] * 0.1
                elif piece.piece_type == chess.BISHOP: val += BISHOP_PST[idx] * 0.1
                elif piece.piece_type == chess.KING: val += KING_PST[idx] * 0.1
            else:
                # В шахматах Фишера даем базовый бонус за захват центра
                row, col = chess.square_rank(square), chess.square_file(square)
                if 2 <= row <= 5 and 2 <= col <= 5:
                    val += 0.15
                    
            if piece.color == chess.WHITE: score += val
            else: score -= val
    return score

def minimax(board, depth, alpha, beta, is_maximizing):
    if board.is_repetition(3):
        return 0.0

    if board.is_game_over():
        outcome = board.outcome()
        if outcome and outcome.winner == chess.WHITE: return 10000.0 + depth
        elif outcome and outcome.winner == chess.BLACK: return -10000.0 - depth
        return 0.0

    if depth == 0:
        return evaluate_board(board)

    # Умная сортировка ходов: взятия и шахи проверяем первыми
    ordered_moves = sorted(board.legal_moves, key=lambda m: (board.is_capture(m), board.gives_check(m)), reverse=True)

    if is_maximizing:
        best = -float('inf')
        for move in ordered_moves:
            board.push(move)
            val = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha: break
        return best
    else:
        best = float('inf')
        for move in ordered_moves:
            board.push(move)
            val = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha: break
        return best

def find_best_move(board, depth):
    """ Ищет ход, учитывая Дебютную книгу, Черный список и Минимакс """
    my_color = board.turn
    
    # 1. Проверяем Дебютную книгу (только для классических шахмат)
    if not board.chess960:
        move_history = " ".join([m.uci() for m in board.move_stack])
        if move_history in OPENING_BOOK:
            book_choices = OPENING_BOOK[move_history]
            legal_book = [chess.Move.from_uci(m) for m in book_choices if chess.Move.from_uci(m) in board.legal_moves]
            if legal_book:
                chosen = random.choice(legal_book)
                print(f"📖 [Книга] Найден встроенный дебютный ход: {chosen.uci()}")
                return chosen, evaluate_board(board)

    # 2. Обычный просчет, если дебют кончился или это Chess960
    short_fen = " ".join(board.fen().split()[:3])
    legal_moves_list = list(board.legal_moves)
    random.shuffle(legal_moves_list)
    ordered_moves = sorted(legal_moves_list, key=lambda m: (board.is_capture(m), board.gives_check(m)), reverse=True)
    
    best_move = None
    alpha, beta = -float('inf'), float('inf')
    known_bad_moves = bad_moves_db.get(short_fen, [])

    if my_color == chess.WHITE:
        best_score = -float('inf')
        for move in ordered_moves:
            move_uci = move.uci()
            board.push(move)
            if move_uci in known_bad_moves: score = -9000.0
            else: score = minimax(board, depth - 1, alpha, beta, False)
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
            if move_uci in known_bad_moves: score = 9000.0
            else: score = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            
    if not best_move and legal_moves_list:
        best_move = random.choice(legal_moves_list)
        best_score = evaluate_board(board)
        
    return best_move, best_score

# ================= 4. СЕТЕВАЯ МНОГОПОТОЧНОСТЬ LICHESS =================

TOKEN = "lip_XG5jv7YWcOFKO1Sg6RRG"
session = berserk.TokenSession(TOKEN)
client = berserk.Client(session)

my_username = client.account.get()['username']
my_id = client.account.get()['id']

MAX_CONCURRENT_GAMES = 2  
active_games = set()
sent_welcomes = set()   
sent_goodbyes = set()   

def auto_challenger():
    print(f"📡 Авто-поиск запущен!")
    time.sleep(5)
    while True:
        try:
            if len(active_games) >= MAX_CONCURRENT_GAMES:
                time.sleep(5)
                continue
            
            time_controls = [(180, 2), (300, 0), (300, 3)]
            limit, inc = random.choice(time_controls)
            
            # Бот теперь бросает вызовы И в классику, И в шахматы Фишера (chess960)
            variant = random.choice(['standard', 'chess960'])
            
            online_bots = list(client.bots.get_online_bots())
            valid_bots = [b['id'] for b in online_bots if b.get('id') != my_id]
            
            if valid_bots:
                target_username = random.choice(valid_bots)
                print(f"🔥 Вызов к @{target_username} ({variant.upper()})")
                client.challenges.create(username=target_username, rated=True, clock_limit=limit, clock_increment=inc, variant=variant)
                time.sleep(40)  
            else: time.sleep(10)
        except Exception: time.sleep(15)

def handle_game(game_id):
    global active_games, sent_welcomes, sent_goodbyes
    print(f"⚔️ Старт потока для игры {game_id}")
    
    board = None
    moves = []
    my_color = None
    my_moves_history = [] 
    draw_offered_by_me = False 

    try:
        for state in client.bots.stream_game_state(game_id):
            state_type = state.get('type')
            game_data = None

            if state_type == 'gameFull':
                # ОПРЕДЕЛЯЕМ ВАРИАНТ ИГРЫ (Фишер или Стандарт)
                variant_key = state.get('variant', {}).get('key', 'standard')
                is_chess960 = (variant_key == 'chess960')
                
                # Загружаем правильный FEN начальной позиции
                initial_fen = state.get('initialFen', chess.STARTING_FEN)
                if initial_fen == 'startpos':
                    initial_fen = chess.STARTING_FEN
                
                # Важно: инициализируем доску с флагом chess960!
                board = chess.Board(initial_fen, chess960=is_chess960)
                if is_chess960:
                    print(f"⚠️ [{game_id}] ОБНАРУЖЕНЫ ШАХМАТЫ ФИШЕРА (CHESS960)! Режим активирован.")
                
                white_id = state.get('white', {}).get('id', '')
                black_id = state.get('black', {}).get('id', '')
                if white_id.lower() == my_username.lower(): my_color = chess.WHITE
                elif black_id.lower() == my_username.lower(): my_color = chess.BLACK
                
                if game_id not in sent_welcomes:
                    sent_welcomes.add(game_id)
                    try: client.bots.post_message(game_id, "Привет! Сыграем в рейтинговый матч! 😉")
                    except Exception: pass
                        
                game_data = state.get('state', {})
            
            elif state_type == 'gameState':
                game_data = state

            if game_data and board is not None:
                raw_moves = game_data.get('moves', '')
                all_moves = raw_moves.split() if raw_moves else []
                
                while len(moves) < len(all_moves):
                    board.push_uci(all_moves[len(moves)])
                    moves.append(all_moves[len(moves)-1])

                # Логика ничьих
                draw_offer = game_data.get('drawOffer')
                opponent_color_str = 'white' if my_color == chess.BLACK else 'black'
                if draw_offer == opponent_color_str:
                    my_current_score = evaluate_board(board) if my_color == chess.WHITE else -evaluate_board(board)
                    if my_current_score > 1.2:
                        try: client.bots.handle_draw(game_id, accept=False)
                        except Exception: pass
                    else:
                        try: client.bots.handle_draw(game_id, accept=True)
                        except Exception: pass

                status = game_data.get('status')
                if status in ['mate', 'resign', 'draw', 'stalemate', 'timeout', 'outoftime', 'aborted']:
                    winner = game_data.get('winner') 
                    if winner:
                        i_lost = (winner == 'white' and my_color == chess.BLACK) or (winner == 'black' and my_color == chess.WHITE)
                        if i_lost and my_moves_history:
                            bad_fen, bad_move = my_moves_history[-1]
                            save_bad_move(bad_fen, bad_move)
                    break

            # Ход бота
            if board is not None and my_color is not None and board.turn == my_color and not board.is_game_over():
                current_fen = board.fen() 
                
                # Считаем ход на глубину 3
                move, score = find_best_move(board, depth=3)
                my_score = score if my_color == chess.WHITE else -score
                
                print(f"📈 [{game_id}] Оценка позиции: {f'{my_score:+.2f}' if abs(my_score) < 5000 else 'МАТ'}")
                
                if my_score < -2.5 and not draw_offered_by_me:
                    try:
                        client.bots.handle_draw(game_id, accept=True)
                        draw_offered_by_me = True
                    except Exception: pass
                
                if move:
                    move_uci = move.uci()
                    time.sleep(0.1)
                    try:
                        client.bots.make_move(game_id, move_uci)
                        my_moves_history.append((current_fen, move_uci))
                    except Exception as m_err:
                        print(f"⚠️ Сбой отправки хода: {m_err}")

    except Exception as e:
        print(f"💥 Ошибка в потоке игры {game_id}: {e}")
    finally:
        active_games.discard(game_id)

# ================= 5. МУЛЬТИСТАРТ =================

load_memory() 
print(f"Робот {my_username} полностью пересобран. Запуск систем...")

threading.Thread(target=auto_challenger, daemon=True).start()

while True:
    try:
        for event in client.bots.stream_incoming_events():
            if event.get('type') == 'challenge':
                challenge_id = event.get('challenge', {}).get('id')
                # Принимаем как стандарт, так и chess960
                v_name = event.get('challenge', {}).get('variant', {}).get('key', 'standard')
                
                if challenge_id and v_name in ['standard', 'chess960']:
                    if len(active_games) < MAX_CONCURRENT_GAMES:
                        client.bots.accept_challenge(challenge_id)
                    else:
                        client.bots.decline_challenge(challenge_id, reason='later')

            elif event.get('type') == 'gameStart':
                game_id = event.get('game', {}).get('id')
                if game_id not in active_games and len(active_games) < MAX_CONCURRENT_GAMES:
                    active_games.add(game_id)
                    threading.Thread(target=handle_game, args=(game_id,), daemon=True).start()

    except Exception as e:
        time.sleep(5)
def run_web_server():
    # Render передает строку, нужно убедиться, что мы слушаем на 0.0.0.0
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    print(f"🌐 [Web Server] Успешно запущен на порту {port}!")
    server.serve_forever()
