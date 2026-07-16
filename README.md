# 🏥 Clinic Booking API

> A production-ready RESTful API built with **Django** and **Django REST Framework** for managing doctor appointments, enforcing business rules, preventing double bookings, and demonstrating clean backend architecture, automated testing, CI/CD, and cloud deployment.

---

# Live Demo

### 🌐 Base API URL

```text
https://clinic-booking-api-dwb4.onrender.com
```

### Health Check

GET

https://clinic-booking-api-dwb4.onrender.com/api/health/

---

# GitHub Repository

(Add your GitHub repository URL here)

---

# Test Coverage

✅ 95 Automated Tests

✅ 99.41% Code Coverage

---

# Built With

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- Gunicorn
- Render
- GitHub Actions
- Ruff
- Pytest
- Coverage.py

---

# Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Business Problem](#2-business-problem)
- [3. Solution Overview](#3-solution-overview)
- [4. Critical Thinking Part 1 – Designing the Domain Model](#4-critical-thinking-part-1--designing-the-domain-model)
- [5. Critical Thinking Part 2 – Designing Business Rules](#5-critical-thinking-part-2--designing-business-rules)
- [6. System Architecture](#6-system-architecture)
- [7. Project Structure](#7-project-structure)
- [8. Database Design](#8-database-design)
- [9. Business Rules Explained](#9-business-rules-explained)
- [10. API Documentation](#10-api-documentation)
- [11. Running the Project Locally](#11-running-the-project-locally)
- [12. Automated Testing](#12-automated-testing)
- [13. Deployment](#13-deployment)
- [14. Troubleshooting](#14-troubleshooting)
- [15. Design Decisions](#15-design-decisions)
- [16. Future Improvements](#16-future-improvements)
- [17. AI Reflection](#17-ai-reflection)
- [18. Author](#18-author)

---

# 1. Project Overview

This project implements a RESTful backend API for a medical clinic that allows patients to book appointments with doctors while enforcing real-world scheduling rules.

The objective was not simply to expose CRUD endpoints, but to design a backend capable of representing the clinic's business processes in a maintainable, scalable, and testable way.

The application demonstrates:

- Clean separation of concerns
- Domain-driven thinking
- Validation of business rules
- Automated testing
- Cloud deployment
- Continuous Integration
- Production configuration

Although the project is intentionally small enough to be completed within the assessment timeframe, the architectural decisions mirror those used in larger production systems.

---

# 2. Business Problem

Imagine a clinic that receives hundreds of appointment requests every day.

Several important questions immediately arise:

- How do we prevent two patients from booking the same doctor at the same time?
- How can doctors define their available working hours?
- What happens when an appointment is cancelled?
- How can patients reschedule appointments?
- How can available time slots be calculated automatically?
- How do we ensure invalid bookings never reach the database?

These questions are business problems—not programming problems.

The primary responsibility of a backend engineer is to translate business requirements into software that consistently enforces those rules.

This project was designed with that philosophy in mind.

---

# 3. Solution Overview

The Clinic Booking API manages four primary business entities:

- Doctors
- Patients
- Doctor Working Hours
- Appointments

Using these entities, the API provides endpoints that allow users to:

- View doctor availability
- Create appointments
- Cancel appointments
- Reschedule appointments
- View upcoming patient appointments
- Perform health checks

Every request passes through validation rules before data is written to the database, ensuring that invalid business operations are rejected.

---

# 4. Critical Thinking Part 1 – Designing the Domain Model

## Thinking Like a Software Engineer

One of the biggest lessons from this project is that software development begins long before writing code.

When a client says:

> "We have a clinic where patients book appointments with doctors."

they are **not** asking for Django models.

They are describing how a business operates.

The first task is therefore to identify the business entities that exist within that description.

This process is known as **Domain Modelling**.

Instead of immediately creating APIs, I first identified the nouns hidden inside the client's requirements.

```
Clinic

│

├── Doctors

├── Patients

├── Working Hours

└── Appointments
```

These naturally became the core domain models.

| Business Entity | Software Model |
|-----------------|----------------|
| Doctor | Doctor |
| Patient | Patient |
| Working Hours | DoctorWorkingHour |
| Appointment | Appointment |


The models emerged naturally from understanding how the clinic operates.

That translation, from business language into software, is one of the most important responsibilities of a backend engineer.

## Why Four Models?

### Doctor

A doctor represents someone capable of providing appointments.

Each doctor stores information such as:

- Full name
- Email
- Medical specialization
- Active status

Doctors are independent entities because they exist regardless of whether patients have appointments.

---

### Patient

Patients are separate business entities.

Each patient stores:

- Full name
- Email
- Phone number

Patients may book many appointments over time.

Keeping them separate prevents duplication of patient information.

---

### DoctorWorkingHour

One of the earliest design decisions was realizing that working hours cannot simply be stored inside the Doctor model.

Consider the following schedule:

Monday

08:00–17:00

Tuesday

09:00–15:00

Wednesday

Off

Thursday

08:00–17:00

Friday

10:00–14:00

Attempting to store this directly inside the Doctor model quickly becomes unmanageable.

Instead, each working day is represented by its own record.

```
Doctor

│

├── Monday

├── Tuesday

├── Thursday

└── Friday
```

This design provides flexibility while keeping the data normalized.

---

### Appointment

Appointments represent the relationship between a patient and a doctor.

Rather than storing only a time, an appointment records:

- Doctor
- Patient
- Appointment start time
- Appointment end time
- Current status
- Cancellation details
- Audit timestamps

This model forms the core of the booking system.

---

## Domain Relationships

```
Doctor

│

├── has many Working Hours

│

└── has many Appointments

Patient

│

└── has many Appointments

Appointment

│

├── belongs to one Doctor

└── belongs to one Patient
```

These relationships accurately mirror how appointments function within a real clinic.

By modelling the domain first, the remaining API design became significantly simpler because the software structure naturally reflected the business itself.

---

# 5. Critical Thinking Part 2 – Designing Business Rules

## From Data Storage to Business Logic

Designing the database models solved only half of the problem.

The next challenge was ensuring that the system behaves exactly as a real clinic would.

A database can store almost anything, including invalid data.

For example, without proper validation, a system could accidentally allow:

- A doctor to work from **5:00 PM to 8:00 AM**
- Two patients booking the same doctor at **10:00 AM**
- Duplicate working hours for the same weekday
- A cancelled appointment still blocking future bookings

Simply creating tables does not prevent these scenarios.

The backend must actively enforce business rules before data is saved.

This project therefore treats business rules as first-class citizens rather than relying solely on the frontend.

---

## Business Rule 1 – Prevent Duplicate Working Hours

### Problem

Imagine a doctor accidentally receives these two records.

| Weekday | Start | End |
|---------|-------|------|
| Monday | 08:00 | 17:00 |
| Monday | 09:00 | 16:00 |

Which schedule is correct?

There is no way for the application to know.

This ambiguity would also make availability calculations unreliable.

### Solution

Each doctor may only have **one working-hour record per weekday**.

```
Doctor

↓

Monday

↓

One record only
```

This rule is enforced directly by the database using a unique constraint.

This guarantees data integrity even if another application accesses the database.

---

## Business Rule 2 – Working Hours Must Be Valid

### Problem

The following record is technically possible if no validation exists.

```
Start Time

17:00

End Time

08:00
```

Although these are valid times individually, together they create an impossible work shift.

### Solution

Every working-hour record validates that

```
End Time > Start Time
```

before it is saved.

If this condition fails, Django raises a validation error and rejects the request.

This prevents impossible schedules from entering the system.

---

## Business Rule 3 – Prevent Double Booking

This is the most important business rule in the entire application.

Imagine the following scenario.

```
10:00 AM

↓

Patient A books

↓

BOOKED
```

A few seconds later

```
10:00 AM

↓

Patient B attempts booking
```

Without validation the database would now contain

```
Doctor

↓

10:00

↓

Patient A

↓

10:00

↓

Patient B
```

The doctor cannot attend both appointments.

### Solution

The application ensures that only **one active appointment** may exist for a doctor at a particular start time.

This validation occurs before the appointment is created.

If another booked appointment already exists for that slot, the request is rejected.

---

## Why Q Objects Were Used

One important requirement was that cancelled appointments should release their booking slot.

Suppose this appointment exists.

```
10:00 AM

↓

BOOKED
```

Nobody else should be able to reserve that slot.

However, if the patient later cancels,

```
10:00 AM

↓

CANCELLED
```

the doctor becomes available again.

To achieve this behaviour, the database constraint applies only to appointments whose status is **BOOKED**.

This was implemented using Django's `Q` object.

Conceptually, the rule becomes:

```
Only enforce uniqueness

WHEN

status == BOOKED
```

Instead of

```
Always enforce uniqueness
```

This subtle design decision allows cancelled appointments to remain in the database for audit purposes while immediately making the time slot available again.

This mirrors how real appointment systems behave.

---

## Why Cancelled Appointments Are Never Deleted

A cancelled appointment still contains valuable business information.

It tells us:

- who booked it
- which doctor it belonged to
- when it was originally scheduled
- why it was cancelled
- when it was cancelled

Deleting the appointment would permanently lose this information.

Instead, the appointment status changes from

```
BOOKED

↓

CANCELLED
```

This preserves historical data while freeing the slot for future bookings.

---

# 6. Database Design

The project uses four primary models.

```
                Doctor
                   │
                   │
      ┌────────────┴────────────┐
      │                         │
DoctorWorkingHour        Appointment
                                  │
                                  │
                              Patient
```

---

## Doctor

Represents medical practitioners working at the clinic.

Stores:

- Full Name
- Email Address
- Medical Specialization
- Active Status
- Created Timestamp
- Updated Timestamp

Relationship

```
Doctor

↓

Many Working Hours

↓

Many Appointments
```

---

## Patient

Represents individuals capable of booking appointments.

Stores:

- Full Name
- Email Address
- Phone Number
- Created Timestamp
- Updated Timestamp

Relationship

```
Patient

↓

Many Appointments
```

---

## DoctorWorkingHour

Defines the weekly availability of each doctor.

Stores

- Doctor
- Weekday
- Start Time
- End Time

Purpose

Allows doctors to have different schedules on different days.

Example

```
Monday

08:00–17:00

Tuesday

09:00–15:00

Friday

08:00–12:00
```

---

## Appointment

Represents an actual booking between a patient and a doctor.

Stores

- Doctor
- Patient
- Appointment Start
- Appointment End
- Booking Status
- Cancellation Reason
- Cancellation Timestamp
- Created Timestamp
- Updated Timestamp

Appointment is the central entity of the application because every business operation ultimately affects this model.

---

# 7. Business Workflow

The complete appointment lifecycle is illustrated below.

```
Patient

↓

Check Doctor Availability

↓

Choose Available Slot

↓

Create Appointment

↓

BOOKED

↓

───────────────

Patient keeps appointment

OR

↓

Cancel Appointment

↓

CANCELLED

↓

Slot becomes available again

OR

↓

Reschedule Appointment

↓

New Time

↓

BOOKED
```

Every transition is validated before it is committed to the database.

This prevents inconsistent business states.

---

# 8. API Documentation

The following endpoints expose the functionality of the application.

| Endpoint | Method | Purpose |
|-----------|--------|----------|
| `/api/health/` | GET | Health check |
| `/api/doctors/<doctor_id>/availability/?date=YYYY-MM-DD` | GET | View available slots |
| `/api/appointments/` | POST | Create appointment |
| `/api/appointments/<appointment_id>/cancel/` | PATCH | Cancel appointment |
| `/api/appointments/<appointment_id>/reschedule/` | PATCH | Reschedule appointment |
| `/api/patients/<patient_id>/appointments/` | GET | View patient's upcoming appointments |

---

## API Index

### Health Check

**Method**

GET

**Endpoint**

```
/api/health/
```

Purpose

Confirms that the API is running correctly.

Expected Response

```json
{
    "status": "ok",
    "service": "clinic-booking-api"
}
```

---

### Doctor Availability

**Method**

GET

**Endpoint**

```
/api/doctors/1/availability/?date=2026-07-20
```

Purpose

Calculates every available appointment slot for a doctor on a specific date based on:

- Working hours
- Existing bookings
- Appointment duration

Example Response

```json
{
    "doctor": {
        "id": 1,
        "full_name": "Dr. Maleek Hassan"
    },
    "available_slots": [
        {
            "start_time": "...",
            "end_time": "..."
        }
    ]
}
```

---

### Create Appointment

**Method**

POST

**Endpoint**

```
/api/appointments/
```

Example Request

```json
{
    "doctor_id": 1,
    "patient_id": 1,
    "start_time": "2026-07-20T09:00:00Z"
}
```

Purpose

Books an available appointment slot.

Business Rules

- Doctor must exist
- Patient must exist
- Slot must be inside working hours
- Slot must not already be booked

Returns

HTTP 201 Created

---

### Cancel Appointment

**Method**

PATCH

**Endpoint**

```
/api/appointments/1/cancel/
```

Example Request

```json
{
    "reason": "Patient is unavailable."
}
```

Purpose

Marks the appointment as cancelled.

Business Rules

- Appointment must exist
- Appointment must currently be BOOKED
- Cancellation reason is stored
- Slot immediately becomes available again

Returns

HTTP 200 OK

---

### Reschedule Appointment

**Method**

PATCH

**Endpoint**

```
/api/appointments/1/reschedule/
```

Example Request

```json
{
    "start_time": "2026-07-20T10:00:00Z"
}
```

Purpose

Moves an existing appointment to another valid slot.

Business Rules

- New slot must exist
- New slot must not already be booked
- New slot must fall inside working hours

Returns

HTTP 200 OK

---

### Patient Upcoming Appointments

**Method**

GET

**Endpoint**

```
/api/patients/1/appointments/
```

Purpose

Returns all future active appointments for a patient.

Cancelled appointments are intentionally excluded from the response because they are no longer upcoming appointments.

Returns

HTTP 200 OK

```json
{
    "patient": {
        "id": 1,
        "full_name": "John Dorimee"
    },
    "appointments": [
        {
            "id": 1,
            "status": "BOOKED"
        }
    ]
}
```

---

## API Testing Summary

The deployed API was successfully tested end-to-end on Render.

The following workflows were verified:

- ✅ Health check endpoint
- ✅ Doctor availability calculation
- ✅ Appointment creation
- ✅ Appointment rescheduling
- ✅ Appointment cancellation
- ✅ Patient upcoming appointments
- ✅ Slot release after cancellation
- ✅ Prevention of double booking

---

# 9. Project Structure

The project follows a modular architecture where each component has a single responsibility.

```
clinic_booking_api/

├── appointments/
│   ├── admin.py
│   ├── models.py
│   ├── serializers.py
│   ├── selectors.py
│   ├── services.py
│   ├── validators.py
│   ├── views.py
│   ├── urls.py
│   ├── tests/
│   └── management/
│       └── commands/
│           └── seed_data.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── build.sh
├── manage.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Why This Structure?

One of my design goals was to keep responsibilities separated.

Instead of placing all business logic inside Django views, each layer has a clearly defined responsibility.

| Layer | Responsibility |
|--------|----------------|
| Models | Database structure |
| Serializers | Input validation and output formatting |
| Validators | Business rule validation |
| Selectors | Database queries |
| Services | Business operations |
| Views | HTTP request handling |
| Tests | Verification of business behaviour |

This separation makes the project easier to maintain, test, and extend.

---

# 10. Running the Project Locally

## Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY>

cd clinic_booking_api
```

---

## Create a virtual environment

Windows

```bash
python -m venv .venv
```

Activate

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configure environment variables

Copy

```
.env.example
```

to

```
.env
```

Generate a secure Django secret key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Update

```
DJANGO_SECRET_KEY
```

inside

```
.env
```

---

## Apply migrations

```bash
python manage.py migrate
```

---

## Load demonstration data

```bash
python manage.py seed_data
```

---

## Start the development server

```bash
python manage.py runserver
```

Open

```
http://127.0.0.1:8000/api/health/
```

Expected response

```json
{
    "status":"ok",
    "service":"clinic-booking-api"
}
```

---

# 11. Automated Testing

Testing was treated as an essential part of development rather than an afterthought.

The project contains automated tests covering:

- Model validation
- Business rules
- Appointment booking
- Appointment cancellation
- Appointment rescheduling
- Doctor availability
- Upcoming appointments
- Validation errors
- API responses
- Edge cases

---

## Running Tests

```bash
pytest
```

---

## Running Coverage

```bash
pytest --cov=appointments --cov-report=term-missing
```

Final Results

```
95 Tests Passed

99.41% Coverage
```

High coverage helps reduce regressions by ensuring that critical business behaviour continues to work as the application evolves.

Coverage alone does not guarantee software quality, but it provides confidence that the most important execution paths have been exercised.

---

# 12. Code Quality

To maintain a consistent codebase the project uses Ruff.

Run

```bash
ruff check .

ruff format
```

Benefits

- Consistent formatting
- Static analysis
- Early detection of issues
- Cleaner pull requests

The project was also developed with zero unresolved Pylance errors before submission.

---

# 13. Continuous Integration

Every pull request automatically triggers GitHub Actions.

Workflow

```
Developer

↓

Feature Branch

↓

Pull Request

↓

GitHub Actions

↓

Ruff

↓

Pytest

↓

Coverage

↓

Merge

↓

Render Deployment
```

The CI pipeline verifies that every proposed change passes formatting checks, linting, and automated tests before it reaches the main branch.

This reduces the likelihood of introducing regressions.

---

# 14. Deployment

The project is deployed on Render using PostgreSQL.

Deployment stack

```
GitHub

↓

Render

↓

Gunicorn

↓

Django

↓

PostgreSQL
```

Environment variables

```
DJANGO_SECRET_KEY

DATABASE_URL

DEBUG

ALLOWED_HOSTS

CSRF_TRUSTED_ORIGINS

PYTHON_VERSION
```

Deployment process

```
Push to GitHub

↓

GitHub Actions

↓

Merge into main

↓

Render Automatic Deploy

↓

build.sh

↓

Collect Static Files

↓

Run Migrations

↓

Seed Demo Data

↓

Application Live
```

Live API

```
https://clinic-booking-api-dwb4.onrender.com
```

---

# 15. Troubleshooting

During development several real-world issues were encountered and resolved.

---

## Render Health Check Returned HTTP 400

Cause

Incorrect

```
ALLOWED_HOSTS
```

configuration.

Solution

Updated

```
ALLOWED_HOSTS
```

and

```
CSRF_TRUSTED_ORIGINS
```

to match the Render hostname.

---

## Missing Health Endpoint

Cause

Initial deployment did not expose the health route correctly.

Solution

Verified URL configuration and redeployed after updating Render configuration.

---

## SQLite vs PostgreSQL

During local development SQLite was used because it requires minimal setup and supports rapid iteration.

Production uses PostgreSQL because it offers stronger reliability, concurrency support, and scalability.

The transition between databases is handled automatically using

```
dj-database-url
```

---

## Duplicate Appointment Protection

Prevented using model constraints, validation logic, and transactional booking.

This ensures two concurrent requests cannot create duplicate active bookings.

---

# 16. Design Decisions and Trade-offs

Several architectural decisions were made intentionally.

---

## Why SQLite for Development?

Advantages

- Zero configuration
- Lightweight
- Fast setup
- Perfect for local development

Trade-off

Not suitable for production-scale concurrency.

Therefore PostgreSQL is used in production.

---

## Why Services?

Business logic should not live inside views.

Views should coordinate requests.

Services should perform business operations.

Benefits

- Easier testing
- Reusability
- Cleaner architecture

---

## Why Validators?

Validation rules belong together.

Keeping them separate prevents duplicated validation logic across multiple endpoints.

---

## Why Selectors?

Database queries are isolated from business logic.

Benefits

- Easier optimisation
- Cleaner views
- Better separation of concerns

---

## Why PATCH Instead of PUT?

Cancellation and rescheduling modify only part of an existing appointment.

PATCH communicates partial updates more accurately than PUT.

---

## Why Keep Cancelled Appointments?

Deleting appointments would remove valuable historical information.

Instead the appointment status changes from

```
BOOKED

↓

CANCELLED
```

This preserves an audit trail while releasing the booking slot.

---

# 17. Future Improvements

Potential enhancements include

- JWT Authentication
- User accounts
- Role-based permissions
- Swagger / OpenAPI documentation
- Email notifications
- SMS reminders
- Doctor leave management
- Holiday calendars
- Pagination
- Search endpoints
- Timezone support
- Audit logging
- Bulk appointment cancellation
- Calendar integrations
- Appointment reminders
- Docker containerisation
- Kubernetes deployment
- Redis caching
- Background task processing with Celery

---

# 18. AI Reflection

Artificial Intelligence was used as an engineering assistant throughout the project.

Its primary role was to accelerate development, explain complex Django concepts, review architecture, and provide alternative implementation ideas.

However, every suggestion was critically analysed. With pro's and con's evaluated before adoption.

## Example of Helpful AI Assistance

AI served as an engineering assistant throughout the project by helping me:

- implement the service layer to separate business logic from API views.
- Design reusable validators to enforce business rules consistently.
- Build selectors that isolate database queries from business operations.
- Develop comprehensive automated test suites covering API endpoints, business logic, validation rules, and edge cases.

AI significantly accelerated the development process by generating ideas, explaining complex concepts, and suggesting implementation approaches. However, every suggestion was critically reviewed, adapted where necessary, and validated through manual testing, code reviews, linting, and automated test execution before being incorporated into the project.

---

## Example of Incorrect AI Guidance

During development AI occasionally suggested recreating functionality that had already been implemented, such as rebuilding service-layer components that already existed.

Instead of accepting the suggestion, I compared it with the current project structure, identified the duplication, and continued extending the existing implementation.

Another example occurred during deployment when the initial environment configuration did not match the automatically assigned Render hostname, resulting in failed health checks.

The issue was diagnosed using deployment logs and corrected by updating the environment variables.

---

## Lessons Learned

The most valuable lesson from this project is that AI should be treated as an engineering assistant rather than an authority.

Successful software development still requires:

- Critical thinking
- Testing
- Verification
- Understanding business requirements
- Debugging
- Independent decision-making

---

# 19. Conclusion

This project demonstrates much more than the ability to build REST endpoints.

It demonstrates the complete software engineering lifecycle:

- Understanding business requirements
- Designing a domain model
- Enforcing business rules
- Building maintainable APIs
- Writing automated tests
- Measuring code coverage
- Applying Continuous Integration
- Deploying to the cloud
- Troubleshooting production issues
- Documenting engineering decisions

The final result is a production-ready backend application that accurately models a real clinic booking workflow while following modern Django development practices.

---

# 20. Author

**John Reinhard Raduma**

Tech Support Engineer

Built using

- Python
- Django
- Django REST Framework
- PostgreSQL
- Render
- GitHub Actions

# 🚀 Quick Evaluation Guide

To help reviewers evaluate the project quickly, the examples below use the following sample data loaded by the `seed_data` management command.

### Test Data

```text
Doctor ID : 5
Patient ID: 3
```

> **Important**
>
> Before creating or rescheduling an appointment, first use the Doctor Availability endpoint to identify an available future appointment slot.

---

# Live API

Base URL

```
https://clinic-booking-api-dwb4.onrender.com
```

---

# Endpoint Index

| Feature | Method | Live URL |
|----------|--------|----------|
| Health Check | GET | https://clinic-booking-api-dwb4.onrender.com/api/health/ |
| Doctor Availability | GET | https://clinic-booking-api-dwb4.onrender.com/api/doctors/5/availability/?date=2026-07-20 |
| Patient Upcoming Appointments | GET | https://clinic-booking-api-dwb4.onrender.com/api/patients/3/appointments/ |
| Create Appointment | POST | https://clinic-booking-api-dwb4.onrender.com/api/appointments/ |
| Cancel Appointment | PATCH | https://clinic-booking-api-dwb4.onrender.com/api/appointments/<appointment_id>/cancel/ |
| Reschedule Appointment | PATCH | https://clinic-booking-api-dwb4.onrender.com/api/appointments/<appointment_id>/reschedule/ |

---

# 1. Verify the API is Running

### Request

```http
GET /api/health/
```

### Live URL

```
https://clinic-booking-api-dwb4.onrender.com/api/health/
```

Expected Response

```json
{
    "status": "ok",
    "service": "clinic-booking-api"
}
```

---

# 2. Check Doctor Availability

### Request

```http
GET /api/doctors/5/availability/?date=2026-07-20
```

### Live URL

```
https://clinic-booking-api-dwb4.onrender.com/api/doctors/5/availability/?date=2026-07-20
```

Purpose

Returns every available 30-minute appointment slot for Doctor **5** on the requested date.

Example Response

```json
{
    "doctor": {
        "id": 5,
        "full_name": "Dr. Sarah Kim",
        "specialization": "General Medicine"
    },
    "date": "2026-07-20",
    "slot_duration_minutes": 30,
    "available_slots": [
        {
            "start_time": "2026-07-20T09:00:00Z",
            "end_time": "2026-07-20T09:30:00Z"
        }
    ]
}
```

---

# 3. Create an Appointment

### Request

```http
POST /api/appointments/
Content-Type: application/json
```

### Example Request Body

```json
{
    "doctor_id": 5,
    "patient_id": 3,
    "start_time": "2026-07-20T09:00:00Z"
}
```

### Example cURL

```bash
curl -X POST \
https://clinic-booking-api-dwb4.onrender.com/api/appointments/ \
-H "Content-Type: application/json" \
-d '{
    "doctor_id":5,
    "patient_id":3,
    "start_time":"2026-07-20T09:00:00Z"
}'
```

Expected Response

```
HTTP 201 Created
```

> Save the returned **Appointment ID** because it will be used for rescheduling and cancellation.

---

# 4. View Patient Upcoming Appointments

### Request

```http
GET /api/patients/3/appointments/
```

### Live URL

```
https://clinic-booking-api-dwb4.onrender.com/api/patients/3/appointments/
```

Example Response

```json
{
    "patient": {
        "id": 3,
        "full_name": "Jane Doe"
    },
    "appointments": [
        {
            "id": 4,
            "doctor": {
                "id": 5,
                "full_name": "Dr. Sarah Kim"
            },
            "status": "BOOKED",
            "start_time": "2026-07-20T09:00:00Z"
        }
    ]
}
```

---

# 5. Reschedule an Appointment

Replace `<appointment_id>` with the Appointment ID returned during booking.

### Request

```http
PATCH /api/appointments/<appointment_id>/reschedule/
Content-Type: application/json
```

Example Request

```json
{
    "start_time":"2026-07-20T10:00:00Z"
}
```

Example cURL

```bash
curl -X PATCH \
https://clinic-booking-api-dwb4.onrender.com/api/appointments/4/reschedule/ \
-H "Content-Type: application/json" \
-d '{
    "start_time":"2026-07-20T10:00:00Z"
}'
```

Expected Response

```
HTTP 200 OK
```

Business Rule

- The new slot must exist.
- It must fall within the doctor's working hours.
- It must not already be booked.

---

# 6. Cancel an Appointment

Replace `<appointment_id>` with the Appointment ID returned during booking.

### Request

```http
PATCH /api/appointments/<appointment_id>/cancel/
Content-Type: application/json
```

Example Request

```json
{
    "reason":"Reviewer testing appointment cancellation."
}
```

Example cURL

```bash
curl -X PATCH \
https://clinic-booking-api-dwb4.onrender.com/api/appointments/4/cancel/ \
-H "Content-Type: application/json" \
-d '{
    "reason":"Reviewer testing appointment cancellation."
}'
```

Expected Response

```
HTTP 200 OK
```

Business Rule

- The appointment status changes from **BOOKED** to **CANCELLED**.
- The appointment remains in the database for audit purposes.
- The appointment slot immediately becomes available for future bookings.

---

# Recommended Evaluation Flow

To verify the complete booking lifecycle, reviewers can perform the following sequence:

1. ✅ Verify the Health Check endpoint.
2. ✅ View Doctor **5** availability.
3. ✅ Select an available future appointment slot.
4. ✅ Create a new appointment for Patient **3**.
5. ✅ Retrieve Patient **3**'s upcoming appointments.
6. ✅ Reschedule the appointment.
7. ✅ Verify the updated appointment time.
8. ✅ Cancel the appointment.
9. ✅ Confirm that the appointment no longer appears in the upcoming appointments endpoint.
10. ✅ Verify that the cancelled slot is once again available for booking.

---

# Notes

- Appointment IDs are generated dynamically by the database.
- The example Appointment ID (`4`) is for illustration only.
- Always use the Appointment ID returned by the Create Appointment endpoint.
- If the Render service has been inactive, the first request may take 30–60 seconds while the free instance wakes up.
- Appointment dates should be in the future and fall on a valid working day for Doctor **5**.