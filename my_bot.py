import time
import random
import threading
import json
import os
import berserk
import chess

# ================= 1. ТВОЙ ШАХМАТНЫЙ ДВИЖОК + СИСТЕМА ПАМЯТИ =================

MEMORY_FILE = "bot_memory.json"
memory_lock = threading.Lock()
bad_moves_db = {}

def load_memory():
    """Загружает базу данных плохих ходов из файла"""
    global bad_moves_db
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                bad_moves_db = json.load(f)
            print(f"🧠 Память загружена! Найдено уникальных позиций с ошибками: {len(bad_moves_db)}")
        except Exception as e:
            print(f"⚠️ Не удалось прочитать файл памяти: {e}. Начинаем с чистого листа.")
            bad_moves_db = {}
    else:
        print("🧠 Файл памяти не найден. Будет создан автоматически после первого поражения.")
        bad_moves_db = {}

def save_bad_move(fen, move_uci):
    """Добавляет ход в черный список для конкретной позиции"""
    global bad_moves_db
    with memory_lock:
        # Берем только первые две части FEN (расположение фигур и чей ход),
        # чтобы память работала независимо от прав на рокировку и счетчика ходов
        short_fen = " ".join(fen.split()[:2])
        
        if short_fen not in bad_moves_db:
            bad_moves_db[short_fen] = []
        
        if move_uci not in bad_moves_db[short_fen]:
            bad_moves_db[short_fen].append(move_uci)
            print(f"💾 Ход {move_uci} добавлен в черный список для позиции: {short_fen}")
            
            try:
                with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(bad_moves_db, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Ошибка записи в файл памяти: {e}")

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
            
            row = chess.square_rank(square)
            col = chess.square_file(square)
            
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
    """ Ищет лучший ход, штрафуя ходы из базы ошибок """
    my_color = board.turn
    short_fen = " ".join(board.fen().split()[:2])
    
    legal_moves_list = list(board.legal_moves)
    random.shuffle(legal_moves_list)
    ordered_moves = sorted(legal_moves_list, key=lambda m: board.is_capture(m), reverse=True)
    
    best_move = None
    alpha = -float('inf')
    beta = float('inf')

    # Проверяем, есть ли у нас зафиксированные ошибки в этой позиции
    known_bad_moves = bad_moves_db.get(short_fen, [])

    if my_color == chess.WHITE:
        best_score = -float('inf')
        for move in ordered_moves:
            move_uci = move.uci()
            board.push(move)
            
            # Если ход в черном списке — жестко штрафуем его оценку
            if move_uci in known_bad_moves:
                score = -9000.0  # Для белых это ужасно
                print(f"⚠️ Минимакс заметил ошибку из прошлого ({move_uci}). Применяем штраф.")
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
            
            # Если ход в черном списке — жестко штрафуем его оценку
            if move_uci in known_bad_moves:
                score = 9000.0  # Для черных это ужасно (так как они минимизируют)
                print(f"⚠️ Минимакс заметил ошибку из прошлого ({move_uci}). Применяем штраф.")
            else:
                score = minimax(board, depth - 1, alpha, beta, True)
                
            board.pop()
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            
    return best_move if best_move else random.choice(legal_moves_list)

# ================= 2. НАСТРОЙКИ МНОГОПОТОЧНОСТИ И СЕТИ =================

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
    """ Фоновый поток: ищет соперников, пока лимит одновременных партий не исчерпан """
    print(f"📡 Поток авто-поиска запущен! Лимит одновременных игр: {MAX_CONCURRENT_GAMES}")
    time.sleep(5)
    
    while True:
        try:
            if len(active_games) >= MAX_CONCURRENT_GAMES:
                time.sleep(5)
                continue
            
            time_controls = [
                (180, 2), (300, 0), (300, 3), (600, 0)
            ]
            limit, inc = random.choice(time_controls)
            mode = random.choice(['bot', 'human'])
            target_username = None
            
            if mode == 'bot':
                online_bots = list(client.bots.get_online_bots())
                valid_bots = [b['id'] for b in online_bots if b.get('id') != my_id]
                if valid_bots:
                    target_username = random.choice(valid_bots)
            elif mode == 'human':
                try:
                    leaderboard = client.users.get_leaderboard('blitz', nb=100)
                    pool = [user['id'] for user in leaderboard if 'id' in user]
                    if len(pool) > 40:
                        target_username = random.choice(pool[40:])
                    elif pool:
                        target_username = random.choice(pool)
                except Exception:
                    pass
            
            if target_username and len(active_games) < MAX_CONCURRENT_GAMES:
                print(f"🔥 Отправляем РЕЙТИНГОВЫЙ вызов к @{target_username}")
                client.challenges.create(username=target_username, rated=True, clock_limit=limit, clock_increment=inc)
                time.sleep(40)  
            else:
                time.sleep(10)
        except Exception as e:
            time.sleep(15)

def handle_game(game_id):
    """ Изолированный поток для ведения конкретной партии с записью истории ходов """
    global active_games, sent_welcomes, sent_goodbyes
    print(f"⚔️ Поток для партии {game_id} успешно запущен!")
    
    board = chess.Board()
    moves = []
    my_color = None
    
    # Сюда пишем историю: (FEN до нашего хода, сам сделанный ход в формате UCI)
    my_moves_history = [] 

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
                
                print(f"[{game_id}] Я играю {'белыми' if my_color == chess.WHITE else 'чёрными'}")
                
                if game_id not in sent_welcomes:
                    sent_welcomes.add(game_id)
                    try:
                        client.bots.post_message(game_id, "Привет! Приятной рейтинговой игры! 😊 Удачи!")
                    except Exception:
                        pass
                        
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
                    print(f"[{game_id}] Партия завершена. Статус: {status}")
                    
                    # --- АНАЛИЗ РЕЗУЛЬТАТА И ОБУЧЕНИЕ ---
                    winner = game_data.get('winner') # 'white' или 'black'
                    if winner:
                        i_lost = (winner == 'white' and my_color == chess.BLACK) or (winner == 'black' and my_color == chess.WHITE)
                        if i_lost and my_moves_history:
                            # Берем самый последний сделанный нами ход в этой партии
                            bad_fen, bad_move = my_moves_history[-1]
                            save_bad_move(bad_fen, bad_move)
                            print(f"❌ Партия проиграна. Бот запомнил роковую ошибку: {bad_move}")
                    
                    if game_id not in sent_goodbyes:
                        sent_goodbyes.add(game_id)
                        try:
                            client.bots.post_message(game_id, "Спасибо за партию! Хорошая игра! GG WP 🤝")
                        except Exception:
                            pass
                    break

            if my_color is not None and board.turn == my_color and not board.is_game_over():
                current_fen = board.fen() # Сохраняем позицию до вычисления хода
                
                move = find_best_move(board, depth=3)
                if move:
                    move_uci = move.uci()
                    time.sleep(0.1)
                    try:
                        client.bots.make_move(game_id, move_uci)
                        # Записываем в локальную историю потока
                        my_moves_history.append((current_fen, move_uci))
                        print(f"[{game_id}] Сделал ход: {move_uci}")
                    except Exception as m_err:
                        print(f"⚠️ Не удалось отправить ход: {m_err}")

    except Exception as e:
        print(f"💥 Критическая ошибка в игре {game_id}: {e}")
    finally:
        active_games.discard(game_id)
        print(f"🏁 Поток партии {game_id} закрыт. Свободно слотов: {MAX_CONCURRENT_GAMES - len(active_games)}")

# ================= 3. ЗАПУСК БОТА =================

load_memory() # Подгружаем базу данных ошибок
print(f"Бот {my_username} онлайн. Начинаем фарм с функцией самообучения!")

threading.Thread(target=auto_challenger, daemon=True).start()

while True:
    try:
        for event in client.bots.stream_incoming_events():
            if event.get('type') == 'challenge':
                challenge_id = event.get('challenge', {}).get('id')
                challenger = event.get('challenge', {}).get('challenger', {}).get('id', 'Unknown')
                
                if challenge_id:
                    if len(active_games) < MAX_CONCURRENT_GAMES:
                        client.bots.accept_challenge(challenge_id)
                        print(f"📥 Приняли входящий вызов от {challenger}!")
                    else:
                        client.bots.decline_challenge(challenge_id, reason='later')

            elif event.get('type') == 'gameStart':
                game_id = event.get('game', {}).get('id')
                if game_id not in active_games and len(active_games) < MAX_CONCURRENT_GAMES:
                    active_games.add(game_id)
                    threading.Thread(target=handle_game, args=(game_id,), daemon=True).start()

    except Exception as e:
        print(f"🚨 Критическая ошибка в главном потоке: {e}")
        time.sleep(5)
