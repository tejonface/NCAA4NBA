"""
NBA Prospect Schedule - Flask Application
Custom HTML/CSS web app with full design control
"""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, jsonify, g
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import contextmanager

app = Flask(__name__)
DATABASE_URL = os.environ.get('DATABASE_URL')

# Connection pool for database connections
connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL
)

# Template context processor to add current time to all templates
@app.context_processor
def inject_now():
    return {'now': get_eastern_now()}

def get_eastern_now():
    """Get current datetime in Eastern timezone"""
    return datetime.now(ZoneInfo("America/New_York"))

def get_eastern_today():
    """Get today's date in Eastern timezone"""
    return get_eastern_now().date()

@contextmanager
def get_db_connection():
    """Get database connection from pool with proper cleanup"""
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)

def format_game_time(game_date, game_time):
    """Format game date and time as 'Nov 8, 9:00 PM'"""
    if not game_date or not game_time:
        return ""
    try:
        month_day = game_date.strftime('%b %-d')
        return f"{month_day}, {game_time}" if game_time else month_day
    except:
        return ""

@app.route('/')
def index():
    """Home page - Draft Board"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get prospects with their next game
            cur.execute("""
                SELECT 
                    p.rank, p.team_logo_url, p.player, p.school,
                    g.game_date, g.game_time, g.tv_network, g.away_team, g.home_team
                FROM prospects p
                LEFT JOIN game_prospects gp ON p.id = gp.prospect_id
                LEFT JOIN games g ON gp.game_id = g.id
                WHERE g.game_date >= %s OR g.game_date IS NULL
                ORDER BY p.rank, g.game_date
            """, (get_eastern_today(),))
            
            prospects = cur.fetchall()
            
            # Get unique prospects with their first upcoming game
            draft_board = {}
            for row in prospects:
                rank = row['rank']
                if rank not in draft_board:
                    draft_board[rank] = {
                        'rank': rank,
                        'team_logo_url': row['team_logo_url'],
                        'player': row['player'],
                        'school': row['school'],
                        'game_time_et': format_game_time(row['game_date'], row['game_time']),
                        'tv_network': row['tv_network'] or 'None',
                        'away_team': row['away_team'] or '',
                        'home_team': row['home_team'] or ''
                    }
            
            draft_board_list = sorted(draft_board.values(), key=lambda x: x['rank'])
            
            return render_template('draft_board.html', prospects=draft_board_list)

@app.route('/super-matchups')
def super_matchups():
    """Games with prospects on both teams"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Find games with prospects on both teams
            cur.execute("""
                SELECT 
                    g.id, g.game_date, g.game_time, g.away_team, g.home_team, g.tv_network,
                    COUNT(DISTINCT gp.prospect_id) as prospect_count,
                    COUNT(DISTINCT CASE WHEN gp.team = g.away_team THEN gp.prospect_id END) as away_prospects,
                    COUNT(DISTINCT CASE WHEN gp.team = g.home_team THEN gp.prospect_id END) as home_prospects
                FROM games g
                JOIN game_prospects gp ON g.id = gp.game_id
                WHERE g.game_date >= %s
                GROUP BY g.id, g.game_date, g.game_time, g.away_team, g.home_team, g.tv_network
                HAVING COUNT(DISTINCT CASE WHEN gp.team = g.away_team THEN gp.prospect_id END) > 0
                   AND COUNT(DISTINCT CASE WHEN gp.team = g.home_team THEN gp.prospect_id END) > 0
                ORDER BY g.game_date, g.game_time
            """, (get_eastern_today(),))
            
            games = cur.fetchall()
            
            # Get players for each game
            matchups = []
            for game in games:
                cur.execute("""
                    SELECT p.rank, p.player, p.school, gp.team
                    FROM game_prospects gp
                    JOIN prospects p ON gp.prospect_id = p.id
                    WHERE gp.game_id = %s
                    ORDER BY p.rank
                """, (game['id'],))
                
                players = cur.fetchall()
                
                # Group players by school
                schools = {}
                for player in players:
                    school = player['school']
                    if school not in schools:
                        schools[school] = []
                    schools[school].append(player)
                
                matchups.append({
                    'away_team': game['away_team'],
                    'home_team': game['home_team'],
                    'game_time_et': format_game_time(game['game_date'], game['game_time']),
                    'tv_network': game['tv_network'] or 'None',
                    'schools': schools
                })
            
            return render_template('super_matchups.html', matchups=matchups)

@app.route('/games-by-date')
def games_by_date():
    """Calendar view of games"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all games with prospects
            cur.execute("""
                SELECT DISTINCT g.game_date, COUNT(DISTINCT g.id) as game_count
                FROM games g
                JOIN game_prospects gp ON g.id = gp.game_id
                WHERE g.game_date >= %s
                GROUP BY g.game_date
                ORDER BY g.game_date
            """, (get_eastern_today(),))
            
            date_counts = {row['game_date']: row['game_count'] for row in cur.fetchall()}
            
            return render_template('games_by_date.html', date_counts=date_counts, today=get_eastern_today())

@app.route('/api/games/<date_str>')
def games_for_date(date_str):
    """API endpoint to get games for a specific date"""
    try:
        game_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT
                    g.away_team, g.home_team, g.game_time, g.tv_network
                FROM games g
                JOIN game_prospects gp ON g.id = gp.game_id
                WHERE g.game_date = %s
                ORDER BY g.game_time
            """, (game_date,))
            
            games = cur.fetchall()
            
            # Get players for each game
            result = []
            for game in games:
                cur.execute("""
                    SELECT p.rank, p.player, p.school
                    FROM game_prospects gp
                    JOIN prospects p ON gp.prospect_id = p.id
                    JOIN games g ON gp.game_id = g.id
                    WHERE g.game_date = %s AND g.away_team = %s AND g.home_team = %s
                    ORDER BY p.rank
                """, (game_date, game['away_team'], game['home_team']))
                
                players = cur.fetchall()
                
                # Group by school
                schools = {}
                for player in players:
                    school = player['school']
                    if school not in schools:
                        schools[school] = []
                    schools[school].append({'rank': player['rank'], 'player': player['player']})
                
                result.append({
                    'away_team': game['away_team'],
                    'home_team': game['home_team'],
                    'game_time': format_game_time(game_date, game['game_time']),
                    'tv_network': game['tv_network'] or 'None',
                    'schools': schools
                })
            
            return jsonify(result)

@app.route('/distribution')
def distribution():
    """Prospect distribution by school/country"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT school, COUNT(*) as count
                FROM prospects
                GROUP BY school
                ORDER BY count DESC, school
            """)
            
            schools = cur.fetchall()
            
            return render_template('distribution.html', schools=schools)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
