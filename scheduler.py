from datetime import date

from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from database import engine
from models import Extinguisher, Notification


def check_due_extinguishers():
    db = Session(engine)

    try:
        today = date.today()

        extinguishers = db.query(Extinguisher).all()

        for extinguisher in extinguishers:

            if not extinguisher.next_service_date:
                continue

            service_date = date.fromisoformat(
                str(extinguisher.next_service_date)
            )

            if service_date <= today:

                # Check if notification already exists
                existing_notification = db.query(Notification).filter(
                    Notification.extinguisher_id == extinguisher.id,
                    Notification.notification_type == "SERVICE_DUE"
                ).first()

                # Don't create duplicate notification
                if existing_notification:
                    continue

                notification = Notification(
                    customer_id=extinguisher.customer_id,
                    extinguisher_id=extinguisher.id,
                    notification_type="SERVICE_DUE",
                    message=f"Service is due for extinguisher {extinguisher.extinguisher_no}"
                )

                db.add(notification)

                print(
                    f"🔔 Notification created: "
                    f"Extinguisher {extinguisher.extinguisher_no}"
                )

        db.commit()

    finally:
        db.close()


scheduler = BackgroundScheduler()

scheduler.add_job(
    check_due_extinguishers,
    "interval",
    seconds=30
)

scheduler.start()