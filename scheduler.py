from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import engine
from models import Extinguisher, Notification


def check_due_extinguishers():
    db = Session(engine)

    try:
        today = date.today()
        next_30_days = today + timedelta(days=30)
        extinguishers = db.query(Extinguisher).all()

        for extinguisher in extinguishers:
            # Skip inactive extinguishers
            if extinguisher.status and extinguisher.status.lower() != "active":
                continue

            if not extinguisher.next_service_date:
                continue

            try:
                service_date = date.fromisoformat(
                    str(extinguisher.next_service_date)
                )
            except (ValueError, TypeError):
                continue

            if service_date <= today:
                # 1. Service is DUE (overdue or due today)
                existing_due = db.query(Notification).filter(
                    Notification.extinguisher_id == extinguisher.id,
                    Notification.notification_type == "SERVICE_DUE",
                    Notification.is_read == False
                ).first()

                if not existing_due:
                    try:
                        # Auto-resolve any prior upcoming notification now that it is due
                        db.query(Notification).filter(
                            Notification.extinguisher_id == extinguisher.id,
                            Notification.notification_type == "SERVICE_UPCOMING",
                            Notification.is_read == False
                        ).update({Notification.is_read: True}, synchronize_session=False)

                        notification = Notification(
                            customer_id=extinguisher.customer_id,
                            extinguisher_id=extinguisher.id,
                            notification_type="SERVICE_DUE",
                            message=f"Service is due for extinguisher {extinguisher.extinguisher_no}"
                        )
                        db.add(notification)
                        db.flush()
                        print(
                            f"[NOTIFICATION] Service DUE notification created: "
                            f"Extinguisher {extinguisher.extinguisher_no}"
                        )
                    except IntegrityError:
                        db.rollback()
                        continue

            elif today < service_date <= next_30_days:
                # 2. Service is UPCOMING (within next 30 days)
                existing_upcoming = db.query(Notification).filter(
                    Notification.extinguisher_id == extinguisher.id,
                    Notification.notification_type == "SERVICE_UPCOMING",
                    Notification.is_read == False
                ).first()

                if not existing_upcoming:
                    try:
                        days_left = (service_date - today).days
                        day_text = f"in {days_left} day{'s' if days_left > 1 else ''}"
                        notification = Notification(
                            customer_id=extinguisher.customer_id,
                            extinguisher_id=extinguisher.id,
                            notification_type="SERVICE_UPCOMING",
                            message=f"Upcoming service for extinguisher {extinguisher.extinguisher_no} {day_text} ({extinguisher.next_service_date})"
                        )
                        db.add(notification)
                        db.flush()
                        print(
                            f"[NOTIFICATION] Upcoming notification created: "
                            f"Extinguisher {extinguisher.extinguisher_no} ({day_text})"
                        )
                    except IntegrityError:
                        db.rollback()
                        continue

        db.commit()

    except Exception as e:
        print(f"Error in scheduler check_due_extinguishers: {e}")
        db.rollback()
    finally:
        db.close()


scheduler = BackgroundScheduler()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            check_due_extinguishers,
            "interval",
            seconds=30,
            id="check_due_extinguishers_job",
            replace_existing=True
        )
        scheduler.start()
        print("[SCHEDULER] Background scheduler started (interval: 30s)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[SCHEDULER] Background scheduler stopped")