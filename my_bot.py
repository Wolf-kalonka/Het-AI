import time
import random
import threading
import json
import os
import traceback
import berserk
import chess

# ================= 1. ДЕБЮТНЫЕ КНИГИ (OPENING BOOKS) =================

OPENING_BOOK = {
    "": ["e2e4", "d2d4", "g1f3", "c4c4"],
    "e2e4 e7e5": ["g1f3"],
    "e2e4 e7e5 g1f3": ["b8c6"],
    "e2e4 e7e5 g1f3 b8c6": ["b1b5", "b1c4", "d2d4"],
    "e2e4 c7c5": ["g1f3", "b1c3"],
    "e2e4 c7c5 g1f3": ["d7d6", "e7e6", "b8c6"],
    "e2e4 c7c5 g1f3 d7d6": ["d2d4"],
    "d2d4 d7d5": ["c4c4"],
    "d2d4 d7d5 c4c4": ["e7e6", "c7c6"],
    "e2e4": ["c7c5", "e7e5", "e7e6", "c7c6"],
    "d2d4": ["d7d5", "g8f6"],
    "g1f3": ["d7d5", "g8f6"],
    "c4c4": ["e7e5", "c7c5"],
    "e2e4 c7c5 g1f3": ["d7d6", "b8c6"],
    "e2e4 c7c5 g1f3 d7d6 d2d4": ["c5d4"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4": ["g8f6"],
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3": ["a7a6", "g7g6"],
}

# ================= 2. ПОЗИЦИОННЫЕ МАТРИЦЫ =================

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

# ================= 3. ЛОКАЛЬНАЯ ПАМЯТЬ =================

MEMORY_FILE = "bot_memory.json"
memory_lock = threading.Lock()
bad_moves_db = {}

def load_memory():
    global bad_moves_db
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                bad_moves_db = json.load(f)
            print(f"🧠 Память успешно загружена! Записей ошибок: {len(bad_moves_db)}")
        except Exception as e:
            print(f"⚠️ Не удалось прочитать файл памяти (запустимся с пустой): {e}")
            bad_moves_db = {}

def save_bad_move(fen, move_uci):
    global bad_moves_db
    with memory_lock:
        short_fen = " ".join(fen.split()[:3])
        if short_fen not in bad_moves_db:
            bad_moves_db[short_fen] = []
        if move_uci not in bad_moves_db[short_fen]:
            bad_moves_db[short_fen].append(move_uci)
            print(f"💾 Зафиксирована ошибка на Личессе! Ход {move_uci} сохранен для: {short_fen}")
            try:
                with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(bad_moves_db, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Ошибка записи файла памяти на виртуальный диск Actions: {e}")

# ================= 4. ДВИЖОК МИНИМАКСА =================

def evaluate_board(board):
    piece_values = {
        chess.PAWN: 1.0, chess.KNIGHT: 3.1, chess.BISHOP: 3.25,
        chess.ROOK: 5.0, chess.QUEEN: 9.0, chess.KING: 0.0
    }
    score = 0.0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = piece_values[piece.piece_type]
            idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
            if not board.chess960:
                if piece.piece_type == chess.PAWN: val += PAWN_PST[idx] * 0.1
                elif piece.piece_type == chess.KNIGHT: val += KNIGHT_PST[idx] * 0.1
                elif piece.piece_type == chess.BISHOP: val += BISHOP_PST[idx] * 0.1
                elif piece.piece_type == chess.KING: val += KING_PST[idx] * 0.1
            else:
                row, col = chess.square_rank(square), chess.square_file(square)
                if 2 <= row <= 5 and 2 <= col <= 5: val += 0.15
            if piece.color == chess.WHITE: score += val
            else: score -= val
    return score

def minimax(board, depth, alpha, beta, is_maximizing):
    if board.is_repetition(3): return 0.0
    if board.is_game_over():
        outcome = board.outcome()
        if outcome and outcome.winner == chess.WHITE: return 10000.0 + depth
        elif outcome and outcome.winner == chess.BLACK: return -10000.0 - depth
        return 0.0
    if depth == 0: return evaluate_board(board)

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
    my_color = board.turn
    if not board.chess960:
        move_history = " ".join([m.uci() for m in board.move_stack])
        if move_history in OPENING_BOOK:
            book_choices = OPENING_BOOK[move_history]
            legal_book = [chess.Move.from_uci(m) for m in book_choices if chess.Move.from_uci(m) in board.legal_moves]
            if legal_book:
                chosen_book_move = random.choice(legal_book)
                print(f"📖 [Книга] Найден известный ход: {chosen_book_move.uci()}")
                return chosen_book_move, evaluate_board(board)

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
    return best_move, evaluate_board(board)

# ================= 5. ШАХМАТНЫЙ ЦИКЛ LICHESS =================

TOKEN = os.environ.get("LICHESS_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: Переменная окружения LICHESS_TOKEN не найдена в GitHub Secrets!")
    exit(1)

def run_chess_bot():
    load_memory()
    session = berserk.TokenSession(TOKEN)
    client = berserk.Client(session)
    
    my_username = client.account.get()['username']
    my_id = client.account.get()['id']
    print(f"🚀 Шахматный бот @{my_username} успешно авторизован в Lichess!")

    active_games = set()
    MAX_CONCURRENT_GAMES = 2

    # Поток автоматического поиска соперников-ботов
    def auto_challenger():
        print("📡 Модуль автоматического вызова ботов запущен.")
        while True:
            try:
                if len(active_games) < MAX_CONCURRENT_GAMES:
                    online_bots = [b['id'] for b in client.bots.get_online_bots() if b.get('id') != my_id]
                    if online_bots:
                        target = random.choice(online_bots)
                        print(f"⚔️ Отправляем вызов боту @{target}")
                        client.challenges.create(username=target, rated=True, clock_limit=180, clock_increment=2, variant='standard')
                time.sleep(40)
            except Exception as e:
                print(f"⚠️ Предупреждение авто-вызова: {e}")
                time.sleep(15)

    threading.Thread(target=auto_challenger, daemon=True).start()

    # Поток обработки конкретной шахматной партии
    def handle_game(game_id):
        print(f"⚙️ Создан изолированный поток для обработки партии: {game_id}")
        try:
            board = None
            my_color = None
            moves_count = 0
            my_history = []
            
            for state in client.bots.stream_game_state(game_id):
                if state.get('type') == 'gameFull':
                    board = chess.Board(state.get('initialFen', chess.STARTING_FEN))
                    white_id = state.get('white', {}).get('id', '')
                    my_color = chess.WHITE if white_id.lower() == my_username.lower() else chess.BLACK
                    print(f"🎯 Игра {game_id} инициализирована. Цвет бота: {'Белые' if my_color == chess.WHITE else 'Черные'}")
                    game_state = state.get('state', {})
                else:
                    game_state = state

                raw_moves = game_state.get('moves', '').split()
                while moves_count < len(raw_moves):
                    board.push_uci(raw_moves[moves_count])
                    moves_count += 1

                status = game_state.get('status')
                if status in ['mate', 'resign', 'draw', 'timeout', 'stalemate', 'outoftime']:
                    print(f"🏁 Партия {game_id} завершена. Статус: {status}")
                    if game_state.get('winner') and my_history:
                        winner = game_state['winner']
                        if (winner == 'white' and my_color == chess.BLACK) or (winner == 'black' and my_color == chess.WHITE):
                            # Если проиграли, отправляем последний сделанный ход в список ошибочных
                            save_bad_move(my_history[-1][0], my_history[-1][1])
                    break

                if board.turn == my_color and not board.is_game_over():
                    current_fen = board.fen()
                    move, score = find_best_move(board, depth=3)
                    if move:
                        move_uci = move.uci()
                        print(f"📈 [{game_id}] Выбран ход: {move_uci} (Оценка позиции: {score:+.2f})")
                        try:
                            client.bots.make_move(game_id, move_uci)
                            my_history.append((current_fen, move_uci))
                        except Exception as e:
                            print(f"❌ Не удалось передать ход {move_uci} через API Личесса: {e}")
        except Exception as e:
            print(f"💥 КРИТИЧЕСКАЯ ОШИБКА в логике партии {game_id}: {e}")
            traceback.print_exc()
        finally:
            active_games.discard(game_id)
            print(f"🗑️ Партия {game_id} удалена из пула активных процессов.")

    # Главный прослушиватель событий (Event Stream) Личесса
    print("📥 Запускаем основной бесконечный цикл обработки событий...")
    while True:
        try:
            for event in client.bots.stream_incoming_events():
                event_type = event.get('type')
                
                if event_type == 'challenge':
                    c_id = event['challenge']['id']
                    challenger = event['challenge']['challenger']['id']
                    if len(active_games) < MAX_CONCURRENT_GAMES:
                        print(f"🤝 Принимаем входящий вызов от {challenger} (ID: {c_id})")
                        client.bots.accept_challenge(c_id)
                    else:
                        print(f"🚫 Отклоняем вызов от {challenger}, так как пул игр заполнен.")
                        client.bots.decline_challenge(c_id, reason='later')
                        
                elif event_type == 'gameStart':
                    g_id = event['game']['id']
                    if g_id not in active_games:
                        active_games.add(g_id)
                        threading.Thread(target=handle_game, args=(g_id,), daemon=True).start()
        except Exception as e:
            print(f"⚠️ Сбой сетевого подключения потока Личесс. Перезапуск через 5 сек... Ошибка: {e}")
            traceback.print_exc()
            time.sleep(5)

# ================= 6. ТОЧКА ВХОДА ДЛЯ GITHUB ACTIONS =================

if __name__ == '__main__':
    print("⏳ Инициализация запуска на GitHub Actions...")
    try:
        # Запускаем всё напрямую на главном потоке.
        # Процесс замрет здесь и будет работать 24/7, пока воркфлоу активен.
        run_chess_bot()
    except KeyboardInterrupt:
        print("Бот принудительно остановлен пользователем.")
