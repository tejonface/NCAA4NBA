-- NBA Prospect Schedule Database Schema
-- PostgreSQL Database Schema for Flask Application

-- Drop existing tables if they exist
DROP TABLE IF EXISTS game_prospects CASCADE;
DROP TABLE IF EXISTS games CASCADE;
DROP TABLE IF EXISTS prospects CASCADE;

-- Prospects table: stores NBA draft prospects
CREATE TABLE prospects (
    id SERIAL PRIMARY KEY,
    rank INTEGER NOT NULL,
    team VARCHAR(100),
    team_logo_url TEXT,
    player VARCHAR(200) NOT NULL,
    height VARCHAR(20),
    weight VARCHAR(20),
    position VARCHAR(20),
    school VARCHAR(200),
    conference VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Games table: stores NCAA basketball game schedule
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    game_date DATE NOT NULL,
    game_time VARCHAR(50),
    away_team VARCHAR(200) NOT NULL,
    home_team VARCHAR(200) NOT NULL,
    tv_network VARCHAR(100),
    venue VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_date, away_team, home_team)
);

-- Junction table: links prospects to games they're playing in
CREATE TABLE game_prospects (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    prospect_id INTEGER REFERENCES prospects(id) ON DELETE CASCADE,
    team VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, prospect_id)
);

-- Indexes for performance
CREATE INDEX idx_prospects_rank ON prospects(rank);
CREATE INDEX idx_prospects_school ON prospects(school);
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_game_prospects_game ON game_prospects(game_id);
CREATE INDEX idx_game_prospects_prospect ON game_prospects(prospect_id);

-- Comments for documentation
COMMENT ON TABLE prospects IS '2026 NBA Draft prospects from nbadraft.net';
COMMENT ON TABLE games IS 'NCAA basketball game schedule from ESPN';
COMMENT ON TABLE game_prospects IS 'Junction table linking prospects to their games';
