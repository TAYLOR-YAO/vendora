# Vendora Platform

Vendora is a modern, multi-tenant e-commerce and inventory management platform designed to provide businesses with a robust and scalable solution for managing their online presence, stores, and stock.

The backend is built with Python and the Django REST Framework, following best practices for building scalable, secure, and maintainable web APIs.

## Core Architectural Principles

*   **Multi-Tenancy:** The entire platform is built around a multi-tenant architecture. Every resource, from businesses and products to inventory records, is isolated to a specific tenant. This allows for securely serving multiple customers from a single, shared infrastructure.
*   **Service-Oriented (Django Apps):** The project is organized into decoupled Django applications, each responsible for a distinct business domain. This modular design promotes separation of concerns and makes the system easier to maintain and extend.
*   **API-First Design:** Vendora is headless. It exposes a comprehensive RESTful API that front-end applications (web, mobile) can consume. All business logic is contained within the backend.
*   **Role-Based Access Control (RBAC):** A flexible RBAC system allows tenant administrators to define roles and assign permissions to users at different scopes (e.g., tenant-wide admin, business manager, store operator).

## Technology Stack

*   **Backend:** Python
*   **Framework:** Django & Django REST Framework
*   **Authentication:** `dj-rest-auth` and `django-allauth` for robust token-based authentication, including social login (e.g., Google).
*   **Database:** Uses Django's ORM, making it compatible with PostgreSQL, MySQL, and other relational databases.

## Application Modules (Django Apps)

The backend is composed of several key applications:

### 1. `platformapp`

This is the core application that manages the multi-tenancy structure and platform-wide concerns.

*   **`Tenant`**: Represents an individual customer account on the platform. All other data is scoped to a tenant.
*   **`Role` & `UserRole`**: Implements the Role-Based Access Control (RBAC) system. Defines permissions (e.g., 'admin', 'manager') and assigns them to users within a tenant's context.
*   **`AuditLog`**: Tracks important events and changes within the system for security and compliance.

### 2. `identity`

Handles user identity, authentication, and API access.

*   **`User`**: A custom Django user model using email as the primary identifier and a UUID primary key.
*   **Authentication Views**: Provides endpoints for user registration, login/logout, and social authentication (Google).
*   **`ApiClient`**: Manages API keys for programmatic access to the platform.

### 3. `business`

Manages the core entities that represent a tenant's commercial operations.

*   **`Business`**: The central entity for a tenant, representing their brand or company. It holds settings for currency, language, and branding.
*   **`Store`**: Represents a physical or virtual location, such as a retail store, a warehouse, or a pickup center. Each business can have multiple stores.
*   **`Address`**: A reusable model for storing physical addresses for businesses and stores.

### 4. `inventory`

Provides a comprehensive inventory management system.

*   **`Warehouse`**: A logical or physical location where stock is held. It can be linked to a `Store`.
*   **`StockItem`**: Tracks the quantity of a specific product variant in a specific warehouse (`qty_on_hand`, `qty_reserved`).
*   **`StockLedger`**: An immutable log of all stock movements (adjustments, transfers, sales), providing a complete history for auditing.
*   **`StockReservation`**: Manages the reservation of stock for customer orders.
*   **`StockAdjustment` & `StockTransfer`**: Models for operational tasks like manual stock counts and moving inventory between warehouses. These actions are automatically reflected in the `StockItem` and `StockLedger` via Django signals.

### 5. `commerce` (Inferred)

While not fully provided, this application is responsible for e-commerce-specific logic.

*   **`Product` & `Variant`**: Manages the product catalog.
*   **`Order` & `OrderItem`**: Manages customer orders and the items within them.

## API Design

The API is designed to be clean, consistent, and easy to use.

*   **Tenant Scoping**: All requests to tenant-specific endpoints must include the `X-Tenant-ID` header to specify the tenant context.
*   **Authentication**: Endpoints are secured and require a valid authentication token, except for public endpoints like user registration.
*   **Permissions**: Custom permission classes ensure that users can only access or modify data according to their assigned roles and scope (e.g., a store manager can only manage their assigned store).
*   **Filtering and Searching**: List endpoints support powerful filtering and searching capabilities via query parameters, powered by `django-filter`.
*   **Standardized Views**: The API uses Django REST Framework's `ModelViewSet` to provide standard CRUD endpoints for most resources, ensuring consistency.

## Getting Started

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd vendora/backend
    ```

2.  **Set up the environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**
    Create a `.env` file and configure database settings, secret keys, etc.

4.  **Run database migrations:**
    ```bash
    python manage.py migrate
    ```

5.  **Create a superuser:**
    ```bash
    python manage.py createsuperuser
    ```

6.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

The API will be available at `http://127.0.0.1:8000/`.
