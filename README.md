# MOTORA (موتورا) — Luxury Automotive Import Marketplace

**MOTORA** is a private, exclusive automotive marketplace and online showroom specializing in importing and selling world-class used vehicles from international markets (Germany, South Korea, UAE / Gulf Specs, USA) to customers in Egypt.

---

## 💎 Project Concept & Sole Admin Architecture
- **Single-Owner Model**: Owned, governed, and managed strictly by **ONE ADMIN**. No external dealers or unverified sellers can list vehicles.
- **Full Administrative Independence**: The owner has 100% control over every vehicle, image, video, pricing in EGP, inventory quantities, customer bookings, and live shipment tracking stages directly through the admin dashboard without writing or editing any code.
- **Bilingual Interface**: Arabic (RTL) as the primary language with instant toggle to English (LTR).

---

## 🚀 Key Features

### 1. Vehicle Management System (No Limits)
- Add as many vehicles as needed without any interface or database constraints.
- Fields: Brand, Model, Year, Trim / Category, Country of Origin, Engine Capacity, Fuel Type, Transmission, Mileage (KM), Exterior Color, Interior Color, Vehicle Condition, Chassis (VIN) Number, Available Units, Selling Price in EGP, Reservation Deposit, Expected Delivery Days, Full Arabic/English Descriptions, Technical Specs JSON, and Additional Notes.
- **Media Management**:
  - Multi-file drag-and-drop uploader for high-resolution photos and videos.
  - Set cover image with one click.
  - Image captions and reordering.
  - Video walkaround support.
  - Save as Draft (`hidden`) or Publish (`available`).
  - One-click listing duplication (instant cloning).

### 2. Real-Time Inventory Control
- Track active stock quantities.
- Stock statuses: `Available`, `Reserved`, `Sold`, `Hidden (Draft)`.
- Auto-decrements available units when a reservation is approved.
- Automatic prevention of overbooking when stock reaches 0.
- In-place quick price and quick status updates in the admin table.

### 3. Customer Reservation System
- Direct reservation request modal on every vehicle card and detail page.
- Auto-generates unique reservation references (e.g., `MTR-2026-7842`).
- Admin can review, approve, reject, or manage deposits.
- One-click direct WhatsApp link to customer with prefilled booking notes.

### 4. 9-Stage Vehicle Tracking System (Live Tracking Portal)
Each confirmed booking receives a private tracking page (`/tracking/[booking_code]`):
1. **Reservation Confirmed** (تم تأكيد الحجز والتعاقد)
2. **Vehicle Purchased in Origin Country** (شراء وفحص السيارة ببلد المنشأ)
3. **Preparing for International Shipment** (تجهيز السيارة للشحن الدولي)
4. **Shipped from Origin Country** (انطلاق الشحنة البحرية)
5. **In Transit Across Sea to Egypt** (السيارة في طريقها البحري إلى مصر)
6. **Arrived at Alexandria / Sokhna Port** (وصول الشحنة للموانئ المصرية)
7. **Customs Clearance & Inspection** (إجراءات التخليص الجمركي والفحص والتثمين)
8. **Ready for Showroom Handover** (السيارة جاهزة للاستلام بصالة العرض)
9. **Delivered Successfully to Customer** (تم تسليم السيارة والمستندات للعميل)

*The owner updates each stage with timestamps, geographical locations, inspector notes, and uploads real evidence photos (inspection reports, container loading, customs release certificate) which appear live on the customer's tracking page!*

---

## 🔑 Default Admin Credentials

- **Admin Login Portal**: `http://127.0.0.1:8000/admin/login`
- **Username**: `admin`
- **Password**: `motora2026admin`

*(Password can be changed at any time in the Admin Settings panel).*

---

## 🛠️ Tech Stack & Directory Structure

- **Backend**: FastAPI, Uvicorn, Python 3.12, SQLite (`motora.db`)
- **Frontend**: Tailwind CSS, Font Awesome 6.5, Jinja2, Vanilla JavaScript
- **Security**: PBKDF2-HMAC-SHA256 password hashing, tamper-proof HMAC-signed session cookies
- **File Uploads**: Async multipart streaming to `static/uploads/vehicles/` and `static/uploads/tracking/`

```
motora/
├── app/
│   ├── main.py              # Application entrypoint & static mount
│   ├── database.py          # SQLite schema & seed fleet loader
│   ├── auth.py              # Password hashing & session guards
│   ├── templates.py         # Unified Jinja2 rendering & custom filters
│   └── routers/
│       ├── public.py        # Customer routes (home, vehicles, detail, tracking, reserve)
│       ├── admin.py         # Admin console (vehicles, inventory, bookings, stages, settings)
│       └── media.py         # Multipart file uploader for images & videos
├── templates/
│   ├── base.html            # Luxury master layout & reservation modal
│   ├── index.html           # Cinematic homepage
│   ├── inventory.html       # Full vehicles catalog with filters
│   ├── vehicle_detail.html  # Vehicle page with gallery & specs
│   ├── tracking.html        # Customer 9-stage tracking timeline
│   ├── how_it_works.html    # Detailed import guide
│   ├── contact.html         # Showroom & WhatsApp contact
│   └── admin/
│       ├── base_admin.html
│       ├── login.html
│       ├── dashboard.html
│       ├── vehicles_list.html
│       ├── vehicle_form.html
│       ├── inventory_manager.html
│       ├── bookings_list.html
│       ├── tracking_manager.html
│       ├── tracking_stage_edit.html
│       └── settings.html
├── static/
│   ├── css/style.css        # Luxury dark automotive design system
│   ├── js/main.js           # Client modal, lightbox & gallery handlers
│   ├── js/admin.js          # Admin uploaders & quick status handlers
│   └── uploads/             # Real photos & videos storage
├── run.py                   # One-click startup script
├── test_suite.py            # Automated end-to-end verification tests
└── motora.db                # SQLite database (auto-created on startup)
```

---

## 🏃 Running the Application

1. Open PowerShell / Terminal in the project directory:
   ```powershell
   cd "C:\Users\SHOEIB TEK\.gemini\antigravity\scratch\motora"
   ```

2. Start the server:
   ```powershell
   python run.py
   ```

3. Open in your browser:
   - **Showroom Homepage**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - **Vehicles Showcase**: [http://127.0.0.1:8000/vehicles](http://127.0.0.1:8000/vehicles)
   - **Live Sample Tracking**: [http://127.0.0.1:8000/tracking/MTR-2026-7842](http://127.0.0.1:8000/tracking/MTR-2026-7842)
   - **Admin Dashboard**: [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login)
