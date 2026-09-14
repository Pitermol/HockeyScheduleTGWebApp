import time
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

# Импортируем клиент из твоего файла
from nhl_ext_api import NHLClient #

app = FastAPI(title="Hockey Web App API")

# Разрешаем CORS, чтобы JS мог делать запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализируем клиент; ключи API не требуются для публичных эндпоинтов
nhl = NHLClient() #[cite: 1]
CACHE = {}
CACHE_TTL = 300

@app.get("/api/matches")
def get_matches(date: str = Query("0"), league: str = Query("ALL")):
    # 1. Генерируем уникальный ключ для даты и лиги
    cache_key = f"{date}_{league}"
    
    # 2. Если данные уже есть в кэше и они свежие - отдаем моментально!
    if cache_key in CACHE:
        data, saved_time = CACHE[cache_key]
        if time.time() - saved_time < CACHE_TTL:
            return data

    # 1. Преобразуем -1, 0, 1 в реальные даты для API
    if date in ["-1", "0", "1"]:
        target_date = datetime.utcnow() + timedelta(days=int(date))
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        # Если передали конкретную дату YYYY-MM-DD
        date_str = date

    matches = []

    # 2. Собираем данные НХЛ
    if league in ["NHL", "ALL"]:
        # Получаем данные о счете для конкретной даты YYYY-MM-DD[cite: 1]
        raw_data = nhl.get_score(date_str) #[cite: 1]
        # Обычно матчи лежат в корневом ключе 'games' или внутри 'gameWeek'
        games_list = raw_data.get("games", [])
        if not games_list and "gameWeek" in raw_data:
            for gw in raw_data.get("gameWeek", []):
                if gw.get("date") == date_str:
                    games_list = gw.get("games", [])
                    break

        # Парсим ответ на основе структуры из твоего исходника
        for g in games_list:
            home = g.get("homeTeam", {}) #[cite: 1]
            away = g.get("awayTeam", {}) #[cite: 1]
            
            home_score = home.get("score") #[cite: 1]
            away_score = away.get("score") #[cite: 1]

            if home_score is not None and away_score is not None:
                score_str = f"{home_score}:{away_score}"
            else:
                score_str = "-:-"

            # Определяем статус матча[cite: 1]
            state = g.get("gameState") #[cite: 1]
            if state in {"OFF", "FINAL"}: #[cite: 1]
                time_str = "Завершен"
            elif state == "LIVE":
                time_str = "В игре"
            else:
                # Извлекаем время из startTimeUTC (в формате 2026-09-06T23:00:00Z)[cite: 1]
                start_utc = g.get("startTimeUTC", "") #[cite: 1]
                time_str = start_utc.split("T")[1][:5] if "T" in start_utc else "Ожидается"

            matches.append({
                "id": g.get("id"), #[cite: 1]
                "league": "NHL",
                "teamHome": home.get("abbrev", "Неизвестно"), #[cite: 1]
                "teamAway": away.get("abbrev", "Неизвестно"), #[cite: 1]
                "score": score_str,
                "time": time_str
            })

    # TODO: Добавить аналогичный блок для парсера КХЛ, 
    # а затем сделать матчам matches.extend(khl_matches)
    CACHE[cache_key] = ({"status": "success", "matches": matches}, time.time())
    return {"status": "success", "matches": matches}

# --- Эндпоинты на будущее для страницы профиля и прогнозов ---

@app.get("/api/team/{team}/form")
async def get_team_form_api(team: str, games: int = 5):
    """
    Возвращает компактную сводку о недавней форме команды[cite: 1].
    Использует расписание сезона команды и извлекает boxscore для завершенных игр[cite: 1].
    """
    return nhl.get_team_form(team, games) #[cite: 1]

@app.get("/api/match/{game_id}/analysis")
async def get_match_analysis_api(game_id: int):
    """
    Строит компактную аналитическую сводку (удобно для ИИ-прогнозов)[cite: 1].
    """
    return nhl.get_match_analysis(game_id) #[cite: 1]

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
