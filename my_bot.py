import time
import random
import threading
import berserk
import chess

# ================= 1. ТВОЙ ШАХМАТНЫЙ ДВИЖОК =================

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
    """ Ищет лучший ход со случайным выбором при равных оценках """
    my_color = board.turn
    
    legal_moves_list = list(board.legal_moves)
    random.shuffle(legal_moves_list)
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

# ================= 2. МНОГОПОТОЧНАЯ СИСТЕМА И АВТО-ВЫЗОВЫ =================

TOKEN = "lip_XG5jv7YWcOFKO1Sg6RRG"
session = berserk.TokenSession(TOKEN)
client = berserk.Client(session)

my_username = client.account.get()['username']
my_id = client.account.get()['id']

# Сет для контроля активных игр (чтобы не играть 2 партии параллельно на слабом процессоре)
active_games = set()

def auto_challenger():
    """ Фоновый поток: ищет жертв для рейтинга, пока бот свободен """
    print("📡 Поток автоматического поиска соперников запущен!")
    time.sleep(5)
    
    while True:
        try:
            # Если бот прямо сейчас играет — отдыхаем
            if len(active_games) > 0:
                time.sleep(5)
                continue
            
            time_controls = [
                (180, 2),   # Блиц 3+2
                (300, 0),   # Блиц 5+0
                (300, 3),   # Блиц 5+3
                (600, 0)    # Рапид 10+0
            ]
            limit, inc = random.choice(time_controls)
            
            mode = random.choice(['bot', 'human'])
            target_username = None
            
            if mode == 'bot':
                print("🤖 Сканируем онлайн-ботов...")
                online_bots = list(client.bots.get_online_bots())
                valid_bots = [b['id'] for b in online_bots if b.get('id') != my_id]
                if valid_bots:
                    target_username = random.choice(valid_bots)
                    
            elif mode == 'human':
                print("🌍 Ищем человека через лидерборд...")
                try:
                    leaderboard = client.users.get_leaderboard('blitz', nb=100)
                    pool = [user['id'] for user in leaderboard if 'id' in user]
                    if len(pool) > 40:
                        target_username = random.choice(pool[40:])
                    elif pool:
                        target_username = random.choice(pool)
                except Exception as leader_err:
                    print(f"⚠️ Ошибка загрузки топа: {leader_err}")
            
            if target_username and len(active_games) == 0:
                print(f"🔥 Отправляем РЕЙТИНГОВЫЙ вызов к @{target_username} ({limit // 60}+{inc})")
                client.challenges.create(username=target_username, rated=True, clock_limit=limit, clock_increment=inc)
                time.sleep(45)  # Ждем ответа 45 секунд
            else:
                time.sleep(10)
                
        except Exception as e:
            print(f"⚠️ Ошибка в потоке вызовов: {e}")
            time.sleep(15)

def handle_game(game_id):
    """ Изолированный поток для ведения конкретной партии """
    global active_games
    print(f"⚔️ Поток для партии {game_id} успешно запущен!")
    
    board = chess.Board()
    moves = []
    my_color = None
    chat_welcome_sent = False
    chat_goodbye_sent = False

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
                
                if not chat_welcome_sent:
                    try:
                        client.bots.post_message(game_id, "Привет! Приятной рейтинговой игры! 😊 Удачи!")
                        chat_welcome_sent = True
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
                    if not chat_goodbye_sent:
                        try:
                            client.bots.post_message(game_id, "Спасибо за партию! Хорошая игра! GG WP 🤝")
                            chat_goodbye_sent = True
                        except Exception:
                            pass
                    break

            if my_color is not None and board.turn == my_color and not board.is_game_over():
                print(f"[{game_id}] Думаю над ходом...")
                move = find_best_move(board, depth=3)
                if move:
                    time.sleep(0.1)
                    try:
                        client.bots.make_move(game_id, move.uci())
                        print(f"[{game_id}] Сделал ход: {move.uci()}")
                    except Exception as m_err:
                        print(f"⚠️ Не удалось отправить ход: {m_err}")

    except Exception as e:
        print(f"💥 Критическая ошибка в потоке игры {game_id}: {e}")
    finally:
        # Важно: всегда удаляем игру из активных, чтобы освободить бота
        active_games.discard(game_id)
        print(f"🏁 Поток партии {game_id} закрыт.")

# ================= 3. ГЛАВНЫЙ СЛУШАТЕЛЬ (ОСНОВНОЙ ПОТОК) =================

print(f"Бот {my_username} онлайн. Начинаем фарм рейтинга!")

# Запускаем фонового зазывалу
threading.Thread(target=auto_challenger, daemon=True).start()

while True:
    try:
        # Этот цикл теперь НИКОГДА не блокируется играми
        for event in client.bots.stream_incoming_events():
            
            if event.get('type') == 'challenge':
                challenge_id = event.get('challenge', {}).get('id')
                challenger = event.get('challenge', {}).get('challenger', {}).get('id', 'Unknown')
                
                if challenge_id:
                    if len(active_games) == 0:
                        client.bots.accept_challenge(challenge_id)
                        print(f"📥 Приняли входящий вызов от {challenger}!")
                    else:
                        client.bots.decline_challenge(challenge_id, reason='later')
                        print(f"⏳ Отклонили вызов от {challenger}, так как сейчас играем.")

            elif event.get('type') == 'gameStart':
                game_id = event.get('game', {}).get('id')
                if game_id not in active_games:
                    active_games.add(game_id)
                    # Мгновенно перенаправляем игру в отдельный поток!
                    threading.Thread(target=handle_game, args=(game_id,), daemon=True).start()

    except Exception as e:
        print(f"🚨 Критическая ошибка в главном потоке: {e}")
        time.sleep(5)
