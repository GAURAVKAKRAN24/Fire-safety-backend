from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import engine
from models import Customer, Extinguisher, Service, Notification
from schemas import CustomerCreate, ExtinguisherCreate, ServiceCreate
from datetime import date, timedelta

router = APIRouter()

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

# API endpoints for customer and extinguisher management


# Customer Search by name or mobile number endpoint

@router.get("/customers/search")
def search_customers(
    q: str,
    db: Session = Depends(get_db)
):
    customers = db.query(Customer).filter(
        (Customer.name.ilike(f"%{q}%")) |
        (Customer.phone.ilike(f"%{q}%"))
    ).all()

    return customers


# Search for extinguishers by extinguisher number or type endpoint

@router.get("/extinguishers/search")
def search_extinguishers(
    q: str,
    db: Session = Depends(get_db)
):
    extinguishers = db.query(Extinguisher).filter(
        (Extinguisher.extinguisher_no.ilike(f"%{q}%")) |
        (Extinguisher.type.ilike(f"%{q}%"))
    ).all()

    return extinguishers

# Customer post and get endpoints

@router.post("/customers")
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    new_customer = Customer(
        name=customer.name,
        phone=customer.phone,
        address=customer.address
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


# Delete Customer by ID endpoint

@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    db.delete(customer)
    db.commit()

    return {"message": "Customer deleted successfully"}

# Customer update by ID endpoint

@router.put("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    existing_customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not existing_customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    existing_customer.name = customer.name
    existing_customer.phone = customer.phone
    existing_customer.address = customer.address

    db.commit()
    db.refresh(existing_customer)

    return existing_customer


# get customer by ID endpoint

@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    return customer


# get detail of all extinguishers and services for a particular customer endpoint

@router.get("/customers/{customer_id}/details")
def get_customer_details(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    extinguishers = db.query(Extinguisher).filter(
        Extinguisher.customer_id == customer_id
    ).all()

    return {
        "customer": customer,
        "extinguishers": extinguishers
    }


# Customer service history endpoint

@router.get("/customers/{customer_id}/service-history")
def get_customer_service_history(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
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

# Specific extinguisher details for a particular customer endpoint Dashboard

@router.get("/customers/{customer_id}/dashboard")
def get_customer_dashboard(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    today = date.today()
    next_30_days = today + timedelta(days=30)

    extinguishers = db.query(Extinguisher).filter(
        Extinguisher.customer_id == customer_id
    ).all()

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

        service_date = date.fromisoformat(
            str(extinguisher.next_service_date)
        )

        if service_date <= today:
            due_count += 1
        elif service_date <= next_30_days:
            upcoming_count += 1

    return {
        "customer": customer,
        "total_extinguishers": len(extinguishers),
        "due_extinguishers": due_count,
        "upcoming_extinguishers": upcoming_count,
        "total_services": len(services)
    }


# Customer get endpoint

@router.get("/customers")
def get_customers(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    total = db.query(Customer).count()

    customers = (
        db.query(Customer)
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


# Extinguisher post endpoint

@router.post("/extinguishers")
def create_extinguisher(
    extinguisher: ExtinguisherCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == extinguisher.customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    new_extinguisher = Extinguisher(
        **extinguisher.model_dump()  # We are unpacking the request data into the Extinguisher model using model_dump() method otherwise we have to map each field manually
    )

    db.add(new_extinguisher)
    db.commit()
    db.refresh(new_extinguisher)

    return new_extinguisher


# Extinguisher get endpoint

@router.get("/extinguishers")
def get_extinguishers(
    page: int = 1,
    limit: int = 10,
    status: str | None = None,
    db: Session = Depends(get_db)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    query = db.query(Extinguisher)

    if status:
        query = query.filter(
            func.lower(Extinguisher.status) == status.lower()
        )

    total = query.count()

    extinguishers = (
        query
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
    
@router.get("/extinguishers/due") 
def get_due_extinguishers(db: Session = Depends(get_db)):
    today = date.today() 
    extinguishers = db.query(Extinguisher).all() 
    due_extinguishers = [] 

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        try:
            service_date = date.fromisoformat(extinguisher.next_service_date)
        except ValueError:
            continue

    if service_date <= today:
        due_extinguishers.append(extinguisher) 
    return due_extinguishers


@router.get("/extinguishers/upcoming")
def get_upcoming_extinguishers(db: Session = Depends(get_db)):
    today = date.today()
    next_30_days = today + timedelta(days=30)

    extinguishers = db.query(Extinguisher).all()

    upcoming_extinguishers = []

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        service_date = date.fromisoformat(str(extinguisher.next_service_date))

        if today < service_date <= next_30_days:
            upcoming_extinguishers.append(extinguisher)

    return upcoming_extinguishers


# get extinguishers by extinguisher id endpoint

@router.get("/extinguishers/{extinguisher_id}")
def get_extinguisher_by_id(extinguisher_id: int, db: Session = Depends(get_db)):
    extinguisher = db.query(Extinguisher).filter(Extinguisher.id == extinguisher_id).first()
    if not extinguisher:
        raise HTTPException(
            status_code=404,
            detail="Extinguisher not found"
        )
    return extinguisher


# Update extinguisher by ID endpoint

@router.put("/extinguishers/{extinguisher_id}")
def update_extinguisher(
    extinguisher_id: int,
    extinguisher: ExtinguisherCreate,
    db: Session = Depends(get_db)
):
    existing_extinguisher = db.query(Extinguisher).filter(
        Extinguisher.id == extinguisher_id
    ).first()

    if not existing_extinguisher:
        raise HTTPException(
            status_code=404,
            detail="Extinguisher does not exist"
        )

    customer = db.query(Customer).filter(
        Customer.id == extinguisher.customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
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


# get extinguishers by customer id endpoint

@router.get("/customers/{customer_id}/extinguishers")
def get_customer_extinguishers(customer_id: int, db: Session = Depends(get_db)):
    extinguishers = db.query(Extinguisher).filter(Extinguisher.customer_id == customer_id).all()
    return extinguishers


# Service post endpoint

@router.post("/services")
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db)
):

    extinguisher = db.query(Extinguisher).filter(Extinguisher.id == service.extinguisher_id).first()

    if not extinguisher:  # Check if the extinguisher exists in the database
        raise HTTPException(
            status_code=404,
            detail="Extinguisher does not exist"
        )

    new_service = Service(                            # Same like line number 62 in extinguisher post endpoint, we are unpacking the request data into the Service model using model_dump() method otherwise we have to map each field manually
        extinguisher_id=service.extinguisher_id,
        service_type=service.service_type,
        service_date=service.service_date,
        next_service_date=service.next_service_date,
        amount=service.amount,
        remarks=service.remarks
    )
    db.add(new_service)

    # Update extinguisher dates
    extinguisher.last_service_date = service.service_date
    extinguisher.next_service_date = service.next_service_date

    old_notifications = db.query(Notification).filter(
        Notification.extinguisher_id == service.extinguisher_id,
        Notification.notification_type == "SERVICE_DUE",
        Notification.is_read == False
    ).all()

    for notification in old_notifications:
        notification.is_read = True

    db.commit()
    db.refresh(new_service)
    return new_service


# Get service by service id endpoint

@router.put("/services/{service_id}")
def update_service(
    service_id: int,
    service: ServiceCreate,
    db: Session = Depends(get_db)
):
    existing_service = db.query(Service).filter(
        Service.id == service_id
    ).first()

    if not existing_service:
        raise HTTPException(
            status_code=404,
            detail="Service does not exist"
        )

    extinguisher = db.query(Extinguisher).filter(
        Extinguisher.id == service.extinguisher_id
    ).first()

    if not extinguisher:
        raise HTTPException(
            status_code=404,
            detail="Extinguisher does not exist"
        )

    existing_service.extinguisher_id = service.extinguisher_id
    existing_service.service_type = service.service_type
    existing_service.service_date = service.service_date
    existing_service.next_service_date = service.next_service_date
    existing_service.amount = service.amount
    existing_service.remarks = service.remarks

    extinguisher.last_service_date = service.service_date
    extinguisher.next_service_date = service.next_service_date

    db.commit()
    db.refresh(existing_service)

    return existing_service

# Service get endpoint

@router.get("/services")
def get_services(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    total = db.query(Service).count()

    services = (
        db.query(Service)
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


# Service history on a particular extinguisher endpoint

@router.get("/extinguishers/{extinguisher_id}/services")
def get_service_history(extinguisher_id: int, db: Session = Depends(get_db)):
    extinguisher = db.query(Extinguisher).filter(Extinguisher.id == extinguisher_id).first()
    if not extinguisher:
        raise HTTPException(
            status_code=404,
            detail="Extinguisher not found"
        )
    return db.query(Service).filter(Service.extinguisher_id == extinguisher_id).all()


# Service history on a particular extinguisher endpoint

@router.get("/extinguishers/{extinguisher_id}/service-history")
def get_extinguisher_service_history(
    extinguisher_id: int,
    db: Session = Depends(get_db)
):
    extinguisher = db.query(Extinguisher).filter(
        Extinguisher.id == extinguisher_id
    ).first()

    if not extinguisher:
        raise HTTPException(
            status_code=404,
            detail="Extinguisher does not exist"
        )

    services = db.query(Service).filter(
        Service.extinguisher_id == extinguisher_id
    ).order_by(
        Service.service_date.desc()
    ).all()

    return {
        "extinguisher": extinguisher,
        "total_services": len(services),
        "services": services
    }

# Service history on a particular customer endpoint

@router.get("/customers/{customer_id}/services")
def get_customer_services(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
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



# Dashboard endpoint to get total customers, extinguishers, and services

@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    next_30_days = today + timedelta(days=30)

    customers_count = db.query(Customer).count()
    extinguishers = db.query(Extinguisher).all()
    services_count = db.query(Service).count()

    due_count = 0
    upcoming_count = 0

    for extinguisher in extinguishers:
        if not extinguisher.next_service_date:
            continue

        service_date = date.fromisoformat(
            str(extinguisher.next_service_date)
        )

        if service_date <= today:
            due_count += 1

        elif service_date <= next_30_days:
            upcoming_count += 1

    return {
        "total_customers": customers_count,
        "total_extinguishers": len(extinguishers),
        "due_extinguishers": due_count,
        "upcoming_extinguishers": upcoming_count,
        "total_services": services_count
    }


# Notification endpoints

@router.get("/notifications")
def get_notifications(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    total = db.query(Notification).count()

    notifications = (
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
        .order_by(Notification.created_at.desc())
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

# Mark notification as read endpoint

@router.put("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db)
):

    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification does not exist"
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


# unread notifications count endpoint

@router.get("/notifications/unread-count")
def get_unread_notification_count(
    db: Session = Depends(get_db)
):
    unread_count = db.query(Notification).filter(
        Notification.is_read == False
    ).count()

    return {
        "unread_count": unread_count
    }


# Mark all notifications as read endpoint

@router.put("/notifications/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(
        Notification.is_read == False
    ).all()

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return {
        "message": "All notifications marked as read",
        "updated_count": len(notifications)
    }


# Get Notification for a particular customer endpoint

@router.get("/customers/{customer_id}/notifications")
def get_customer_notifications(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer does not exist"
        )

    notifications = db.query(Notification).filter(
        Notification.customer_id == customer_id
    ).order_by(
        Notification.created_at.desc()
    ).all()

    return notifications



# Delete API's

# Delete service by ID endpoint

@router.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(
        Service.id == service_id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service does not exist"
        )

    extinguisher_id = service.extinguisher_id

    db.delete(service)
    db.commit()

    latest_service = (
        db.query(Service)
        .filter(
            Service.extinguisher_id == extinguisher_id
        )
        .order_by(Service.service_date.desc())
        .first()
    )

    extinguisher = db.query(Extinguisher).filter(
        Extinguisher.id == extinguisher_id
    ).first()

    if not extinguisher:
        raise HTTPException(
            status_code=404,
            detail="Extinguisher does not exist"
        )

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
