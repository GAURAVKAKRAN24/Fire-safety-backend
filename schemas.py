from pydantic import BaseModel

class CustomerCreate(BaseModel):
    name: str
    phone: str
    address: str | None = None

class ExtinguisherCreate(BaseModel):
    customer_id: int
    extinguisher_no: str
    type: str
    capacity: str
    purchase_date: str | None = None
    last_service_date: str | None = None
    next_service_date: str | None = None
    status: str | None = "Active"

class ServiceCreate(BaseModel):
    extinguisher_id: int
    service_type: str
    service_date: str
    next_service_date: str | None = None
    amount: int | None = None
    remarks: str | None = None