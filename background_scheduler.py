"""
Background scheduler for automatic data updates

This module provides tiered background scraping:
- Today's games: Every 30 minutes (to catch live game updates)
- Next 7 days: Every 6 hours (for schedule changes)
- Draft board: Daily at 6 AM (for ranking updates)
- Full season: Daily at 6 AM (for long-term schedule)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
import logging
from scraper import (
    update_schedule_partial,
    update_draft_data,
    get_eastern_today,
    get_eastern_now
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataRefreshScheduler:
    """Manages background data refresh jobs with tiered update strategy"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='America/New_York')
        self._setup_jobs()
    
    def _update_today_games(self):
        """Update today's games - runs every 30 minutes"""
        try:
            logger.info("Starting today's games update")
            today = get_eastern_today()
            update_schedule_partial("today", today, today)
            logger.info("Today's games update completed")
        except Exception as e:
            logger.error(f"Error updating today's games: {e}")
    
    def _update_nearfuture_games(self):
        """Update next 7 days - runs every 6 hours"""
        try:
            logger.info("Starting near-future games update")
            today = get_eastern_today()
            tomorrow = today + timedelta(days=1)
            week_end = today + timedelta(days=7)
            update_schedule_partial("nearfuture", tomorrow, week_end)
            logger.info("Near-future games update completed")
        except Exception as e:
            logger.error(f"Error updating near-future games: {e}")
    
    def _update_draft_board(self):
        """Update draft board - runs daily at 6 AM"""
        try:
            logger.info("Starting draft board update")
            update_draft_data()
            logger.info("Draft board update completed")
        except Exception as e:
            logger.error(f"Error updating draft board: {e}")
    
    def _update_full_season(self):
        """Update far-future games (8+ days) - runs daily at 6:30 AM"""
        try:
            logger.info("Starting far-future games update")
            today = get_eastern_today()
            week_start = today + timedelta(days=8)
            # Update next 90 days of far-future games
            far_end = today + timedelta(days=98)
            update_schedule_partial("full", week_start, far_end)
            logger.info("Far-future games update completed")
        except Exception as e:
            logger.error(f"Error updating far-future games: {e}")
    
    def _setup_jobs(self):
        """Set up all scheduled jobs"""
        # Today's games: Every 30 minutes
        self.scheduler.add_job(
            self._update_today_games,
            'interval',
            minutes=30,
            id='update_today_games',
            name='Update Today\'s Games'
        )
        
        # Near-future games (next 7 days): Every 6 hours
        self.scheduler.add_job(
            self._update_nearfuture_games,
            'interval',
            hours=6,
            id='update_nearfuture_games',
            name='Update Near-Future Games'
        )
        
        # Draft board: Daily at 6 AM
        self.scheduler.add_job(
            self._update_draft_board,
            'cron',
            hour=6,
            minute=0,
            id='update_draft_board',
            name='Update Draft Board'
        )
        
        # Far-future games: Daily at 6:30 AM
        self.scheduler.add_job(
            self._update_full_season,
            'cron',
            hour=6,
            minute=30,
            id='update_full_season',
            name='Update Far-Future Games'
        )
        
        logger.info("Scheduled jobs configured:")
        logger.info("  - Today's games: Every 30 minutes")
        logger.info("  - Next 7 days: Every 6 hours")
        logger.info("  - Draft board: Daily at 6:00 AM ET")
        logger.info("  - Far-future games: Daily at 6:30 AM ET")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Background scheduler started")
            return True
        return False
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Background scheduler stopped")
            return True
        return False
    
    def get_job_status(self):
        """Get status of all jobs"""
        jobs = self.scheduler.get_jobs()
        return [(job.id, job.name, str(job.next_run_time)) for job in jobs]
