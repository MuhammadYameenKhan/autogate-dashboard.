"""
Background Tasks (APScheduler)
- Forecast refresh every 6 hours
- Anomaly model retrain every night
- Old forecast cache cleanup weekly
"""
import logging

logger = logging.getLogger(__name__)


def register_tasks(scheduler, app):
    """Register all scheduled jobs."""

    @scheduler.task('interval', id='refresh_forecast', hours=6, misfire_grace_time=300)
    def refresh_all_forecasts():
        with app.app_context():
            try:
                from app.services.forecast_service import generate_forecast
                for period in ('24h', '48h', '72h'):
                    generate_forecast(period)
                logger.info("Forecast cache refreshed for all periods.")
            except Exception as e:
                logger.error(f"Forecast refresh failed: {e}")

    @scheduler.task('cron', id='cleanup_forecast_cache', hour=3, minute=0)
    def cleanup_old_forecasts():
        """Keep only last 3 forecasts per period."""
        with app.app_context():
            try:
                from app.models import ForecastCache
                from app.extensions import db
                for period in ('24h', '48h', '72h'):
                    entries = (
                        ForecastCache.query
                        .filter_by(period=period)
                        .order_by(ForecastCache.generated_at.desc())
                        .all()
                    )
                    for old in entries[3:]:
                        db.session.delete(old)
                db.session.commit()
                logger.info("Old forecast cache entries cleaned up.")
            except Exception as e:
                logger.error(f"Forecast cleanup failed: {e}")

    @scheduler.task('cron', id='daily_anomaly_report', hour=7, minute=0)
    def daily_anomaly_summary():
        """Log a daily summary of unresolved anomalies."""
        with app.app_context():
            try:
                from app.models import Anomaly
                count = Anomaly.query.filter_by(resolved=False, false_positive=False).count()
                logger.info(f"[Daily Report] Unresolved anomalies: {count}")
            except Exception as e:
                logger.error(f"Daily anomaly report failed: {e}")
