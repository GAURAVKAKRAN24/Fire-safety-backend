from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import engine
from models import Customer, Extinguisher, Service, Notification, User
from schemas import CustomerCreate, ExtinguisherCreate, ServiceCreate
from auth_dependencies import get_current_user, get_db

router = APIRouter()


# -------------------------------------------------------------
# Customer Endpoints
# -------------------------------------------------------------

@router.get("/customers/search")
def search_customers(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query_str = f"%{q.strip()}%"
    customers = (
        db.query(Customer)
        .filter(
            Customer.user_id == current_user.id,
            (Customer.name.ilike(query_str) | Customer.phone.ilike(query_str))
        )
        .all()
    )
    return customers


@router.get("/customers")
def get_customers(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    query = db.query(Customer).filter(Customer.user_id == current_user.id)
    total = query.count()

    customers = (
        query
        .order_by(Customer.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "customers": customers
    }


@router.post("/customers")
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_customer = Customer(
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        user_id=current_user.id
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    return customer


@router.put("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not existing_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    existing_customer.name = customer.name
    existing_customer.phone = customer.phone
    existing_customer.address = customer.address

    db.commit()
    db.refresh(existing_customer)

    return existing_customer


@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    # 1. Delete notifications for this customer
    db.query(Notification).filter(Notification.customer_id == customer_id).delete(synchronize_session=False)

    # 2. Get customer extinguisher IDs
    extinguisher_ids = [
        e.id for e in db.query(Extinguisher.id).filter(Extinguisher.customer_id == customer_id).all()
    ]

    if extinguisher_ids:
        # Delete services for these extinguishers
        db.query(Service).filter(Service.extinguisher_id.in_(extinguisher_ids)).delete(synchronize_session=False)
        # Delete extinguishers
        db.query(Extinguisher).filter(Extinguisher.id.in_(extinguisher_ids)).delete(synchronize_session=False)

    db.delete(customer)
    db.commit()

    return {"message": "Customer deleted successfully"}


@router.get("/customers/{customer_id}/details")
def get_customer_details(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    extinguishers = (
        db.query(Extinguisher)
        .filter(Extinguisher.customer_id == customer_id)
        .all()
    )

    return {
        "customer": customer,
        "extinguishers": extinguishers
    }


@router.get("/customers/{customer_id}/service-history")
def get_customer_service_history(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    services = (
        db.query(
            Service,
            Extinguisher.extinguisher_no,
            Extinguisher.type,
            Extinguisher.capacity
        )
        .join(
            Extinguisher,
            Service.extinguisher_id == Extinguisher.id
        )
        .filter(
            Extinguisher.customer_id == customer_id
        )
        .order_by(Service.service_date.desc())
        .all()
    )

    result = []
    for service, extinguisher_no, extinguisher_type, capacity in services:
        result.append({
            "service": service,
            "extinguisher": {
                "id": service.extinguisher_id,
                "extinguisher_no": extinguisher_no,
                "type": extinguisher_type,
                "capacity": capacity
            }
        })

    return {
        "customer": customer,
        "total_services": len(result),
        "services": result
    }


@router.get("/customers/{customer_id}/dashboard")
def get_customer_dashboard(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    today = date.today()
    next_30_days = today + timedelta(days=30)

    extinguishers = (
        db.query(Extinguisher)
        .filter(Extinguisher.customer_id == customer_id)
        .all()
    )

    services = (
        db.query(Service)
        .join(
            Extinguisher,
            Service.extinguisher_id == Extinguisher.id
        )
        .filter(
            Extinguisher.customer_id == customer_id
        )
        .all()
    )

    due_count = 0
    upcoming_count = 0

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        try:
            service_date = date.fromisoformat(
                str(extinguisher.next_service_date)
            )
            if service_date <= today:
                due_count += 1
            elif service_date <= next_30_days:
                upcoming_count += 1
        except ValueError:
            continue

    return {
        "customer": customer,
        "total_extinguishers": len(extinguishers),
        "due_extinguishers": due_count,
        "upcoming_extinguishers": upcoming_count,
        "total_services": len(services)
    }


@router.get("/customers/{customer_id}/extinguishers")
def get_customer_extinguishers(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    extinguishers = (
        db.query(Extinguisher)
        .filter(Extinguisher.customer_id == customer_id)
        .all()
    )
    return extinguishers


@router.get("/customers/{customer_id}/services")
def get_customer_services(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    services = (
        db.query(Service)
        .join(
            Extinguisher,
            Service.extinguisher_id == Extinguisher.id
        )
        .filter(
            Extinguisher.customer_id == customer_id
        )
        .all()
    )
    return services


@router.get("/customers/{customer_id}/notifications")
def get_customer_notifications(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    notifications = (
        db.query(Notification)
        .filter(
            Notification.customer_id == customer_id
        )
        .order_by(
            Notification.created_at.desc()
        )
        .all()
    )

    return notifications


# -------------------------------------------------------------
# Extinguisher Endpoints
# -------------------------------------------------------------

@router.get("/extinguishers/search")
def search_extinguishers(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query_str = f"%{q.strip()}%"
    extinguishers = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Customer.user_id == current_user.id,
            (Extinguisher.extinguisher_no.ilike(query_str) | Extinguisher.type.ilike(query_str))
        )
        .all()
    )
    return extinguishers


@router.get("/extinguishers")
def get_extinguishers(
    page: int = 1,
    limit: int = 10,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    query = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(Customer.user_id == current_user.id)
    )

    if status:
        query = query.filter(
            func.lower(Extinguisher.status) == status.strip().lower()
        )

    total = query.count()

    extinguishers = (
        query
        .order_by(Extinguisher.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "extinguishers": extinguishers
    }


@router.post("/extinguishers")
def create_extinguisher(
    extinguisher: ExtinguisherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == extinguisher.customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    new_extinguisher = Extinguisher(
        customer_id=extinguisher.customer_id,
        extinguisher_no=extinguisher.extinguisher_no,
        type=extinguisher.type,
        capacity=extinguisher.capacity,
        purchase_date=extinguisher.purchase_date,
        last_service_date=extinguisher.last_service_date,
        next_service_date=extinguisher.next_service_date,
        status=extinguisher.status or "Active"
    )

    db.add(new_extinguisher)
    db.commit()
    db.refresh(new_extinguisher)

    return new_extinguisher


@router.get("/extinguishers/due") 
def get_due_extinguishers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today() 
    extinguishers = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(Customer.user_id == current_user.id)
        .all()
    ) 
    due_extinguishers = [] 

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        try:
            service_date = date.fromisoformat(str(extinguisher.next_service_date))
            if service_date <= today:
                due_extinguishers.append(extinguisher) 
        except ValueError:
            continue

    return due_extinguishers


@router.get("/extinguishers/upcoming")
def get_upcoming_extinguishers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    next_30_days = today + timedelta(days=30)

    extinguishers = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(Customer.user_id == current_user.id)
        .all()
    )

    upcoming_extinguishers = []

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        try:
            service_date = date.fromisoformat(str(extinguisher.next_service_date))
            if today < service_date <= next_30_days:
                upcoming_extinguishers.append(extinguisher)
        except ValueError:
            continue

    return upcoming_extinguishers


@router.get("/extinguishers/{extinguisher_id}")
def get_extinguisher_by_id(
    extinguisher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher not found"
        )

    return extinguisher


@router.put("/extinguishers/{extinguisher_id}")
def update_extinguisher(
    extinguisher_id: int,
    extinguisher: ExtinguisherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not existing_extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher does not exist"
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == extinguisher.customer_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer does not exist"
        )

    existing_extinguisher.customer_id = extinguisher.customer_id
    existing_extinguisher.extinguisher_no = extinguisher.extinguisher_no
    existing_extinguisher.type = extinguisher.type
    existing_extinguisher.capacity = extinguisher.capacity
    existing_extinguisher.purchase_date = extinguisher.purchase_date
    existing_extinguisher.last_service_date = extinguisher.last_service_date
    existing_extinguisher.next_service_date = extinguisher.next_service_date
    existing_extinguisher.status = extinguisher.status

    db.commit()
    db.refresh(existing_extinguisher)

    return existing_extinguisher


@router.delete("/extinguishers/{extinguisher_id}")
def delete_extinguisher(
    extinguisher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher does not exist"
        )

    db.query(Notification).filter(Notification.extinguisher_id == extinguisher_id).delete(synchronize_session=False)
    db.query(Service).filter(Service.extinguisher_id == extinguisher_id).delete(synchronize_session=False)

    db.delete(extinguisher)
    db.commit()

    return {"message": "Extinguisher deleted successfully"}


@router.get("/extinguishers/{extinguisher_id}/services")
def get_service_history(
    extinguisher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher not found"
        )

    return (
        db.query(Service)
        .filter(Service.extinguisher_id == extinguisher_id)
        .all()
    )


@router.get("/extinguishers/{extinguisher_id}/service-history")
def get_extinguisher_service_history(
    extinguisher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher does not exist"
        )

    services = (
        db.query(Service)
        .filter(Service.extinguisher_id == extinguisher_id)
        .order_by(Service.service_date.desc())
        .all()
    )

    return {
        "extinguisher": extinguisher,
        "total_services": len(services),
        "services": services
    }


# -------------------------------------------------------------
# Service Endpoints
# -------------------------------------------------------------

@router.get("/services")
def get_services(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    query = (
        db.query(Service)
        .join(Extinguisher, Service.extinguisher_id == Extinguisher.id)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(Customer.user_id == current_user.id)
    )

    total = query.count()

    services = (
        query
        .order_by(Service.service_date.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "services": services
    }


@router.post("/services")
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == service.extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher does not exist"
        )

    new_service = Service(
        extinguisher_id=service.extinguisher_id,
        service_type=service.service_type,
        service_date=service.service_date,
        next_service_date=service.next_service_date,
        amount=str(service.amount) if service.amount is not None else None,
        remarks=service.remarks
    )
    db.add(new_service)

    # Update extinguisher dates
    extinguisher.last_service_date = service.service_date
    if service.next_service_date:
        extinguisher.next_service_date = service.next_service_date

    # Mark corresponding unread notifications as read
    old_notifications = (
        db.query(Notification)
        .filter(
            Notification.extinguisher_id == service.extinguisher_id,
            Notification.notification_type == "SERVICE_DUE",
            Notification.is_read == False
        )
        .all()
    )

    for notification in old_notifications:
        notification.is_read = True

    db.commit()
    db.refresh(new_service)
    return new_service


@router.put("/services/{service_id}")
def update_service(
    service_id: int,
    service: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_service = (
        db.query(Service)
        .join(Extinguisher, Service.extinguisher_id == Extinguisher.id)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Service.id == service_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not existing_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service does not exist"
        )

    extinguisher = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Extinguisher.id == service.extinguisher_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not extinguisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extinguisher does not exist"
        )

    existing_service.extinguisher_id = service.extinguisher_id
    existing_service.service_type = service.service_type
    existing_service.service_date = service.service_date
    existing_service.next_service_date = service.next_service_date
    existing_service.amount = str(service.amount) if service.amount is not None else None
    existing_service.remarks = service.remarks

    extinguisher.last_service_date = service.service_date
    if service.next_service_date:
        extinguisher.next_service_date = service.next_service_date

    db.commit()
    db.refresh(existing_service)

    return existing_service


@router.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = (
        db.query(Service)
        .join(Extinguisher, Service.extinguisher_id == Extinguisher.id)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(
            Service.id == service_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service does not exist"
        )

    extinguisher_id = service.extinguisher_id

    db.delete(service)
    db.commit()

    latest_service = (
        db.query(Service)
        .filter(Service.extinguisher_id == extinguisher_id)
        .order_by(Service.service_date.desc())
        .first()
    )

    extinguisher = db.query(Extinguisher).filter(Extinguisher.id == extinguisher_id).first()

    if extinguisher:
        if latest_service:
            extinguisher.last_service_date = latest_service.service_date
            extinguisher.next_service_date = latest_service.next_service_date
        else:
            extinguisher.last_service_date = None
            extinguisher.next_service_date = None
        db.commit()

    return {
        "message": "Service deleted successfully",
        "service_id": service_id
    }


# -------------------------------------------------------------
# Dashboard Summary Endpoint
# -------------------------------------------------------------

@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    next_30_days = today + timedelta(days=30)

    customers_count = db.query(Customer).filter(Customer.user_id == current_user.id).count()

    extinguishers = (
        db.query(Extinguisher)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(Customer.user_id == current_user.id)
        .all()
    )

    services_count = (
        db.query(Service)
        .join(Extinguisher, Service.extinguisher_id == Extinguisher.id)
        .join(Customer, Extinguisher.customer_id == Customer.id)
        .filter(Customer.user_id == current_user.id)
        .count()
    )

    due_count = 0
    upcoming_count = 0

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        try:
            service_date = date.fromisoformat(
                str(extinguisher.next_service_date)
            )
            if service_date <= today:
                due_count += 1
            elif service_date <= next_30_days:
                upcoming_count += 1
        except ValueError:
            continue

    return {
        "total_customers": customers_count,
        "total_extinguishers": len(extinguishers),
        "due_extinguishers": due_count,
        "upcoming_extinguishers": upcoming_count,
        "total_services": services_count
    }


# -------------------------------------------------------------
# Notification Endpoints
# -------------------------------------------------------------

@router.get("/notifications")
def get_notifications(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    query = (
        db.query(
            Notification,
            Customer.name,
            Customer.phone,
            Customer.address,
            Extinguisher.extinguisher_no,
            Extinguisher.next_service_date
        )
        .join(
            Customer,
            Notification.customer_id == Customer.id
        )
        .join(
            Extinguisher,
            Notification.extinguisher_id == Extinguisher.id
        )
        .filter(
            Customer.user_id == current_user.id
        )
        .order_by(Notification.created_at.desc())
    )

    total = query.count()

    notifications = (
        query
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    result = []

    for notification, name, phone, address, extinguisher_no, due_date in notifications:
        result.append({
            "id": notification.id,
            "notification_type": notification.notification_type,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
            "customer": {
                "id": notification.customer_id,
                "name": name,
                "phone": phone,
                "address": address
            },
            "extinguisher": {
                "id": notification.extinguisher_id,
                "extinguisher_no": extinguisher_no,
                "due_date": due_date
            }
        })

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "notifications": result
    }


@router.put("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notification = (
        db.query(Notification)
        .join(Customer, Notification.customer_id == Customer.id)
        .filter(
            Notification.id == notification_id,
            Customer.user_id == current_user.id
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification does not exist"
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


@router.get("/notifications/unread-count")
def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    unread_count = (
        db.query(Notification)
        .join(Customer, Notification.customer_id == Customer.id)
        .filter(
            Customer.user_id == current_user.id,
            Notification.is_read == False
        )
        .count()
    )

    return {
        "unread_count": unread_count
    }


@router.put("/notifications/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notifications = (
        db.query(Notification)
        .join(Customer, Notification.customer_id == Customer.id)
        .filter(
            Customer.user_id == current_user.id,
            Notification.is_read == False
        )
        .all()
    )

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return {
        "message": "All notifications marked as read",
        "updated_count": len(notifications)
    }
