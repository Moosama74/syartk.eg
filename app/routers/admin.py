import os
import json
import re
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.database import get_db_connection
from app.templates import render_template
from app.auth import (
    require_admin,
    verify_password,
    create_session_token,
    get_current_admin,
    hash_password
)

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

def slugify(text: str) -> str:
    """Generate a clean URL slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text or "vehicle"

# ----------------- AUTHENTICATION -----------------

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if get_current_admin(request):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "admin/login.html", {"error": None})

@router.post("/login", response_class=HTMLResponse)
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_users WHERE username = ?", (username.strip(),))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        return render_template(
            request,
            "admin/login.html",
            {"error": "اسم المستخدم أو كلمة المرور غير صحيحة / Invalid credentials"},
            status_code=400
        )

    token = create_session_token(user["id"], user["username"])
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="motora_admin_session",
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax"
    )
    return response

@router.get("/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("motora_admin_session")
    return response

# ----------------- DASHBOARD OVERVIEW -----------------

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Metrics
    cursor.execute("SELECT COUNT(*) as total FROM vehicles")
    total_vehicles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as available FROM vehicles WHERE status = 'available'")
    available_vehicles = cursor.fetchone()["available"]

    cursor.execute("SELECT COUNT(*) as reserved FROM vehicles WHERE status = 'reserved'")
    reserved_vehicles = cursor.fetchone()["reserved"]

    cursor.execute("SELECT COUNT(*) as sold FROM vehicles WHERE status = 'sold'")
    sold_vehicles = cursor.fetchone()["sold"]

    cursor.execute("SELECT COUNT(*) as total_bookings FROM bookings")
    total_bookings = cursor.fetchone()["total_bookings"]

    cursor.execute("SELECT COUNT(*) as pending_bookings FROM bookings WHERE status = 'pending'")
    pending_bookings = cursor.fetchone()["pending_bookings"]

    cursor.execute("SELECT COUNT(DISTINCT customer_phone) as total_customers FROM bookings")
    total_customers = cursor.fetchone()["total_customers"]

    cursor.execute("SELECT SUM(selling_price_egp) as total_value FROM vehicles WHERE status != 'hidden'")
    inventory_value = cursor.fetchone()["total_value"] or 0

    cursor.execute("SELECT SUM(deposit_amount) as total_deposits FROM bookings WHERE deposit_paid = 1")
    total_deposits = cursor.fetchone()["total_deposits"] or 0

    # ALL vehicles for instant management directly on the dashboard
    cursor.execute("SELECT * FROM vehicles ORDER BY id DESC")
    all_vehicles = cursor.fetchall()

    # ALL bookings for direct WhatsApp communication and approval
    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.cover_image, v.selling_price_egp, v.vin
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        ORDER BY b.id DESC
    """)
    all_bookings = cursor.fetchall()

    # Recent reservations (top 8)
    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.cover_image, v.selling_price_egp
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        ORDER BY b.id DESC LIMIT 8
    """)
    recent_bookings = cursor.fetchall()

    # Tracked shipments
    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.vin, v.cover_image,
               (SELECT COUNT(*) FROM tracking_stages ts WHERE ts.booking_id = b.id AND ts.status = 'completed') as completed_stages,
               (SELECT stage_title_ar FROM tracking_stages ts WHERE ts.booking_id = b.id AND ts.status = 'in_progress' LIMIT 1) as current_stage_name
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        WHERE b.status IN ('approved', 'active_tracking', 'completed')
        ORDER BY b.id DESC
    """)
    tracked_orders = cursor.fetchall()

    # Showroom Settings
    cursor.execute("SELECT key, value FROM settings")
    settings_rows = cursor.fetchall()
    settings_dict = {row["key"]: row["value"] for row in settings_rows}

    conn.close()

    return render_template(
        request,
        "admin/dashboard.html",
        {
            "admin": admin,
            "stats": {
                "total_vehicles": total_vehicles,
                "available_vehicles": available_vehicles,
                "reserved_vehicles": reserved_vehicles,
                "sold_vehicles": sold_vehicles,
                "total_bookings": total_bookings,
                "pending_bookings": pending_bookings,
                "total_customers": total_customers,
                "inventory_value": inventory_value,
                "total_deposits": total_deposits
            },
            "all_vehicles": all_vehicles,
            "all_bookings": all_bookings,
            "recent_bookings": recent_bookings,
            "tracked_orders": tracked_orders,
            "settings": settings_dict
        }
    )

# ----------------- VEHICLE MANAGEMENT -----------------

@router.get("/vehicles", response_class=HTMLResponse)
async def admin_vehicles_list(
    request: Request,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM vehicles WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if search:
        query += " AND (brand LIKE ? OR model LIKE ? OR vin LIKE ? OR country_of_origin LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    vehicles = cursor.fetchall()
    conn.close()

    return render_template(
        request,
        "admin/vehicles_list.html",
        {
            "admin": admin,
            "vehicles": vehicles,
            "status_filter": status_filter,
            "search": search or ""
        }
    )

@router.get("/vehicles/new", response_class=HTMLResponse)
async def admin_vehicle_create_page(request: Request, admin: dict = Depends(require_admin)):
    return render_template(
        request,
        "admin/vehicle_form.html",
        {
            "admin": admin,
            "vehicle": None,
            "media_items": [],
            "action": "create"
        }
    )

@router.post("/vehicles/new")
async def admin_vehicle_create_submit(
    request: Request,
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    trim: str = Form(""),
    country_of_origin: str = Form(...),
    engine_capacity: str = Form(""),
    fuel_type: str = Form("بنزين (Petrol)"),
    transmission: str = Form("أوتوماتيك"),
    mileage: int = Form(0),
    exterior_color: str = Form("أسود ميتاليك"),
    interior_color: str = Form("جلد فاخر"),
    vehicle_condition: str = Form("فابريكة بالكامل - حالة المصنع"),
    vin: Optional[str] = Form(None),
    units_available: int = Form(1),
    units_total: int = Form(1),
    selling_price_egp: float = Form(...),
    reservation_deposit_egp: float = Form(0),
    expected_delivery_time: str = Form("15 - 25 يوم عمل شامل التخليص"),
    description_ar: str = Form(""),
    description_en: str = Form(""),
    technical_specs: str = Form("{}"),
    additional_notes: str = Form(""),
    features: List[str] = Form([]),
    listing_status: str = Form("available", alias="status"),
    is_featured: int = Form(0),
    is_latest: int = Form(1),
    is_special_offer: int = Form(0),
    cover_image: str = Form(""),
    media_json: str = Form("[]"),
    redirect_to: Optional[str] = Form(None),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate friendly VIN if empty
    vin_candidate = vin.strip() if vin and vin.strip() else f"SYR-{year}-{int(datetime.now().timestamp()) % 100000}"
    cursor.execute("SELECT id FROM vehicles WHERE vin = ?", (vin_candidate,))
    if cursor.fetchone():
        vin_candidate += f"-{int(datetime.now().timestamp()) % 1000}"

    slug_candidate = slugify(f"{brand}-{model}-{year}-{vin_candidate[-6:]}")
    cursor.execute("SELECT id FROM vehicles WHERE slug = ?", (slug_candidate,))
    if cursor.fetchone():
        slug_candidate += f"-{int(datetime.now().timestamp()) % 10000}"

    # Auto-generate Arabic description if empty
    if not description_ar or not description_ar.strip():
        description_ar = f"سيارة {brand} {model} موديل {year} وارد {country_of_origin}، بحالة الزيرو وفابريكة بالكامل بدون أي ملاحظات. تشمل باقة متكاملة من التجهيزات والمواصفات الفاخرة وخضعت للفحص الدقيق قبل الشحن لمصر مع ضمان صالة عرض سيارتك."

    # Parse and incorporate checkboxes into technical_specs
    specs_dict = {}
    try:
        if technical_specs and technical_specs.strip().startswith("{"):
            specs_dict = json.loads(technical_specs)
    except Exception:
        specs_dict = {}

    if features:
        specs_dict["أبرز التجهيزات والمواصفات الأصلية"] = features
    
    final_technical_specs = json.dumps(specs_dict, ensure_ascii=False) if specs_dict else (technical_specs or "{}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Set default cover image if not provided
    media_list = []
    try:
        media_list = json.loads(media_json)
    except Exception:
        pass

    if not cover_image and media_list:
        cover_image = media_list[0].get("url", "")

    cursor.execute("""
        INSERT INTO vehicles (
            slug, brand, model, year, trim, country_of_origin,
            engine_capacity, fuel_type, transmission, mileage,
            exterior_color, interior_color, vehicle_condition, vin,
            units_available, units_total, selling_price_egp, reservation_deposit_egp,
            expected_delivery_time, description_ar, description_en, technical_specs,
            additional_notes, status, is_featured, is_latest, is_special_offer,
            cover_image, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        slug_candidate, brand, model, year, trim, country_of_origin,
        engine_capacity, fuel_type, transmission, mileage,
        exterior_color, interior_color, vehicle_condition, vin_candidate,
        units_available, units_total, selling_price_egp, reservation_deposit_egp,
        expected_delivery_time, description_ar, description_en, final_technical_specs,
        additional_notes, listing_status, is_featured, is_latest, is_special_offer,
        cover_image, now, now
    ))
    vehicle_id = cursor.lastrowid

    # Insert media
    for idx, item in enumerate(media_list):
        cursor.execute("""
            INSERT INTO vehicle_media (vehicle_id, media_type, url, caption, display_order, is_cover, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            item.get("media_type", "image"),
            item.get("url"),
            item.get("caption", ""),
            idx + 1,
            1 if item.get("url") == cover_image else 0,
            now
        ))

    conn.commit()
    conn.close()

    target_url = redirect_to if redirect_to else "/admin/dashboard?tab=vehicles"
    return RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/vehicles/{vehicle_id}/edit", response_class=HTMLResponse)
async def admin_vehicle_edit_page(
    request: Request,
    vehicle_id: int,
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
    vehicle = cursor.fetchone()
    if not vehicle:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found")

    cursor.execute("SELECT * FROM vehicle_media WHERE vehicle_id = ? ORDER BY display_order ASC", (vehicle_id,))
    media_items = cursor.fetchall()
    conn.close()

    return render_template(
        request,
        "admin/vehicle_form.html",
        {
            "admin": admin,
            "vehicle": vehicle,
            "media_items": media_items,
            "action": "edit"
        }
    )

@router.post("/vehicles/{vehicle_id}/edit")
async def admin_vehicle_edit_submit(
    request: Request,
    vehicle_id: int,
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    trim: str = Form(""),
    country_of_origin: str = Form(...),
    engine_capacity: str = Form(""),
    fuel_type: str = Form(...),
    transmission: str = Form(...),
    mileage: int = Form(0),
    exterior_color: str = Form(...),
    interior_color: str = Form(...),
    vehicle_condition: str = Form(...),
    vin: Optional[str] = Form(None),
    units_available: int = Form(1),
    units_total: int = Form(1),
    selling_price_egp: float = Form(...),
    reservation_deposit_egp: float = Form(0),
    expected_delivery_time: str = Form(...),
    description_ar: str = Form(""),
    description_en: str = Form(""),
    technical_specs: str = Form("{}"),
    additional_notes: str = Form(""),
    features: List[str] = Form([]),
    listing_status: str = Form("available", alias="status"),
    is_featured: int = Form(0),
    is_latest: int = Form(1),
    is_special_offer: int = Form(0),
    cover_image: str = Form(""),
    media_json: str = Form("[]"),
    redirect_to: Optional[str] = Form(None),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    vin_candidate = vin.strip() if vin and vin.strip() else f"SYR-{year}-{vehicle_id}"

    if not description_ar or not description_ar.strip():
        description_ar = f"سيارة {brand} {model} موديل {year} وارد {country_of_origin}، بحالة الزيرو وفابريكة بالكامل بدون أي ملاحظات. تشمل باقة متكاملة من التجهيزات والمواصفات الفاخرة وخضعت للفحص الدقيق قبل الشحن لمصر مع ضمان صالة عرض سيارتك."

    # Parse and incorporate checkboxes into technical_specs
    specs_dict = {}
    try:
        if technical_specs and technical_specs.strip().startswith("{"):
            specs_dict = json.loads(technical_specs)
    except Exception:
        specs_dict = {}

    if features:
        specs_dict["أبرز التجهيزات والمواصفات الأصلية"] = features
    
    final_technical_specs = json.dumps(specs_dict, ensure_ascii=False) if specs_dict else (technical_specs or "{}")

    cursor.execute("""
        UPDATE vehicles SET
            brand = ?, model = ?, year = ?, trim = ?, country_of_origin = ?,
            engine_capacity = ?, fuel_type = ?, transmission = ?, mileage = ?,
            exterior_color = ?, interior_color = ?, vehicle_condition = ?, vin = ?,
            units_available = ?, units_total = ?, selling_price_egp = ?, reservation_deposit_egp = ?,
            expected_delivery_time = ?, description_ar = ?, description_en = ?, technical_specs = ?,
            additional_notes = ?, status = ?, is_featured = ?, is_latest = ?, is_special_offer = ?,
            cover_image = ?, updated_at = ?
        WHERE id = ?
    """, (
        brand, model, year, trim, country_of_origin,
        engine_capacity, fuel_type, transmission, mileage,
        exterior_color, interior_color, vehicle_condition, vin_candidate,
        units_available, units_total, selling_price_egp, reservation_deposit_egp,
        expected_delivery_time, description_ar, description_en, final_technical_specs,
        additional_notes, listing_status, is_featured, is_latest, is_special_offer,
        cover_image, now, vehicle_id
    ))

    # Replace media if updated
    try:
        media_list = json.loads(media_json)
        if media_list is not None and len(media_list) > 0:
            cursor.execute("DELETE FROM vehicle_media WHERE vehicle_id = ?", (vehicle_id,))
            for idx, item in enumerate(media_list):
                cursor.execute("""
                    INSERT INTO vehicle_media (vehicle_id, media_type, url, caption, display_order, is_cover, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    vehicle_id,
                    item.get("media_type", "image"),
                    item.get("url"),
                    item.get("caption", ""),
                    idx + 1,
                    1 if item.get("url") == cover_image else 0,
                    now
                ))
    except Exception:
        pass

    conn.commit()
    conn.close()

    target_url = redirect_to if redirect_to else "/admin/dashboard?tab=vehicles"
    return RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)

@router.post("/vehicles/{vehicle_id}/duplicate")
async def admin_vehicle_duplicate(request: Request, vehicle_id: int, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
    v = cursor.fetchone()
    if not v:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rand_suffix = str(int(datetime.now().timestamp()))[-4:]
    new_slug = f"{v['slug']}-copy-{rand_suffix}"
    new_vin = f"{v['vin'][:-4]}{rand_suffix}"

    cursor.execute("""
        INSERT INTO vehicles (
            slug, brand, model, year, trim, country_of_origin,
            engine_capacity, fuel_type, transmission, mileage,
            exterior_color, interior_color, vehicle_condition, vin,
            units_available, units_total, selling_price_egp, reservation_deposit_egp,
            expected_delivery_time, description_ar, description_en, technical_specs,
            additional_notes, status, is_featured, is_latest, is_special_offer,
            cover_image, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_slug, v["brand"], f"{v['model']} (نسخة)", v["year"], v["trim"], v["country_of_origin"],
        v["engine_capacity"], v["fuel_type"], v["transmission"], v["mileage"],
        v["exterior_color"], v["interior_color"], v["vehicle_condition"], new_vin,
        1, 1, v["selling_price_egp"], v["reservation_deposit_egp"],
        v["expected_delivery_time"], v["description_ar"], v["description_en"], v["technical_specs"],
        v["additional_notes"], "available", 0, 1, 0,
        v["cover_image"], now, now
    ))
    new_vehicle_id = cursor.lastrowid

    # Duplicate media
    cursor.execute("SELECT * FROM vehicle_media WHERE vehicle_id = ?", (vehicle_id,))
    for m in cursor.fetchall():
        cursor.execute("""
            INSERT INTO vehicle_media (vehicle_id, media_type, url, caption, display_order, is_cover, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (new_vehicle_id, m["media_type"], m["url"], m["caption"], m["display_order"], m["is_cover"], now))

    conn.commit()
    conn.close()

    referer = request.headers.get("referer")
    if referer and "dashboard" in referer:
        return RedirectResponse(url="/admin/dashboard?tab=vehicles", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/dashboard?tab=vehicles", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/vehicles/{vehicle_id}/delete")
async def admin_vehicle_delete(request: Request, vehicle_id: int, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vehicle_media WHERE vehicle_id = ?", (vehicle_id,))
    cursor.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
    conn.commit()
    conn.close()
    referer = request.headers.get("referer")
    target = referer if (referer and "/admin" in referer) else "/admin/dashboard?tab=vehicles"
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

@router.post("/vehicles/{vehicle_id}/quick-stock")
async def admin_vehicle_quick_stock(
    vehicle_id: int,
    delta: int = Form(0),
    units: Optional[int] = Form(None),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT units_available, units_total, status FROM vehicles WHERE id = ?", (vehicle_id,))
    v = cursor.fetchone()
    if not v:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found")

    current = v["units_available"]
    new_units = units if units is not None else max(0, current + delta)
    new_total = max(v["units_total"], new_units)

    current_status = v["status"]
    if new_units == 0 and current_status == "available":
        new_status = "sold"
    elif new_units > 0 and current_status == "sold":
        new_status = "available"
    else:
        new_status = current_status

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE vehicles SET units_available = ?, units_total = ?, status = ?, updated_at = ?
        WHERE id = ?
    """, (new_units, new_total, new_status, now, vehicle_id))
    conn.commit()
    conn.close()
    return JSONResponse({
        "success": True,
        "units_available": new_units,
        "units_total": new_total,
        "status": new_status
    })

@router.post("/vehicles/{vehicle_id}/quick-status")
async def admin_vehicle_quick_status(
    vehicle_id: int,
    status_val: str = Form(...),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE vehicles SET status = ?, updated_at = ? WHERE id = ?", (
        status_val, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), vehicle_id
    ))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "status": status_val})

@router.post("/vehicles/{vehicle_id}/quick-price")
async def admin_vehicle_quick_price(
    vehicle_id: int,
    price: float = Form(...),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE vehicles SET selling_price_egp = ?, updated_at = ? WHERE id = ?", (
        price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), vehicle_id
    ))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "price": price})

# ----------------- INVENTORY MANAGEMENT -----------------

@router.get("/inventory", response_class=HTMLResponse)
async def admin_inventory_page(
    request: Request,
    filter_type: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM vehicles WHERE 1=1"
    if filter_type == "low_stock":
        query += " AND units_available <= 1 AND status != 'sold'"
    elif filter_type == "out_of_stock":
        query += " AND units_available = 0"
    elif filter_type == "reserved":
        query += " AND status = 'reserved'"

    query += " ORDER BY units_available ASC, id DESC"
    cursor.execute(query)
    vehicles = cursor.fetchall()
    conn.close()

    return render_template(
        request,
        "admin/inventory_manager.html",
        {
            "admin": admin,
            "vehicles": vehicles,
            "filter_type": filter_type
        }
    )

@router.post("/inventory/{vehicle_id}/update-stock")
async def admin_update_stock(
    vehicle_id: int,
    units_available: int = Form(...),
    status_val: Optional[str] = Form(None),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Determine status if available units is 0
    new_status = status_val
    if units_available <= 0 and (not new_status or new_status == 'available'):
        new_status = 'sold'
    elif units_available > 0 and new_status == 'sold':
        new_status = 'available'

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if new_status:
        cursor.execute("""
            UPDATE vehicles SET units_available = ?, status = ?, updated_at = ? WHERE id = ?
        """, (units_available, new_status, now, vehicle_id))
    else:
        cursor.execute("""
            UPDATE vehicles SET units_available = ?, updated_at = ? WHERE id = ?
        """, (units_available, now, vehicle_id))

    conn.commit()
    conn.close()

    return RedirectResponse(url="/admin/inventory", status_code=status.HTTP_303_SEE_OTHER)

# ----------------- BOOKINGS & RESERVATIONS -----------------

@router.get("/bookings", response_class=HTMLResponse)
async def admin_bookings_list(
    request: Request,
    status_filter: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT b.*, v.brand, v.model, v.year, v.cover_image, v.vin, v.selling_price_egp, v.reservation_deposit_egp, v.units_available
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        WHERE 1=1
    """
    params = []
    if status_filter:
        query += " AND b.status = ?"
        params.append(status_filter)

    query += " ORDER BY b.id DESC"
    cursor.execute(query, params)
    bookings = cursor.fetchall()
    conn.close()

    return render_template(
        request,
        "admin/bookings_list.html",
        {
            "admin": admin,
            "bookings": bookings,
            "status_filter": status_filter
        }
    )

@router.post("/bookings/{booking_id}/status")
async def admin_update_booking_status(
    request: Request,
    booking_id: int,
    new_status: str = Form(...),
    deposit_paid: int = Form(0),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()
    if not booking:
        conn.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If approving or activating tracking
    if new_status in ["approved", "active_tracking"] and booking["status"] == "pending":
        # Deduct available vehicle units by 1 and set vehicle to reserved if no more units
        cursor.execute("SELECT units_available FROM vehicles WHERE id = ?", (booking["vehicle_id"],))
        v = cursor.fetchone()
        if v and v["units_available"] > 0:
            remaining = v["units_available"] - 1
            v_status = "reserved" if remaining == 0 else "available"
            cursor.execute("UPDATE vehicles SET units_available = ?, status = ?, updated_at = ? WHERE id = ?", (
                remaining, v_status, now, booking["vehicle_id"]
            ))

        # Check if 9-stage tracking timeline already exists for this booking
        cursor.execute("SELECT COUNT(*) as cnt FROM tracking_stages WHERE booking_id = ?", (booking_id,))
        if cursor.fetchone()["cnt"] == 0:
            # Initialize 9 stages
            stages = [
                (1, "تأكيد الحجز والتعاقد الرسمي", "Reservation Confirmed & Agreement Signed", "completed", now, "صالة عرض سيارتك - القاهرة"),
                (2, "شراء وفحص السيارة ببلد المنشأ", "Vehicle Purchased & Inspected in Origin Country", "in_progress", None, "بلد المنشأ"),
                (3, "تجهيز السيارة للشحن الدولي والتوثيق", "Preparing for International Shipment", "pending", None, "ميناء التصدير"),
                (4, "انطلاق الشحنة من بلد المنشأ", "Shipped from Origin Country", "pending", None, "على متن السفينة الناقلة"),
                (5, "الشحنة في طريقها البحري إلى مصر", "In Transit Across Sea to Egypt", "pending", None, "البحر المتوسط"),
                (6, "وصول الشحنة لميناء الإسكندرية / السخنة", "Arrived at Egyptian Port", "pending", None, "الميناء المصري"),
                (7, "إجراءات التخليص الجمركي والفحص والتثمين", "Customs Clearance & Inspection", "pending", None, "مجمع الجمارك المصري"),
                (8, "السيارة جاهزة للاستلام والترخيص", "Ready for Showroom Handover", "pending", None, "صالة عرض سيارتك"),
                (9, "تم تسليم السيارة والمستندات للعميل", "Delivered to Customer", "pending", None, "مقر العميل")
            ]
            for st in stages:
                cursor.execute("""
                    INSERT INTO tracking_stages (
                        booking_id, stage_number, stage_title_ar, stage_title_en,
                        status, completed_at, location, notes, proof_media
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (booking_id, st[0], st[1], st[2], st[3], st[4], st[5], "تم تحديث المرحلة آلياً فور الموافقة على الحجز.", "[]"))

    cursor.execute("""
        UPDATE bookings SET status = ?, deposit_paid = ?, updated_at = ? WHERE id = ?
    """, (new_status, deposit_paid, now, booking_id))

    conn.commit()
    conn.close()

    referer = request.headers.get("referer")
    if referer and "dashboard" in referer:
        return RedirectResponse(url="/admin/dashboard?tab=bookings", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/bookings", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/bookings/{booking_id}/delete")
async def admin_delete_booking(request: Request, booking_id: int, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tracking_stages WHERE booking_id = ?", (booking_id,))
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    referer = request.headers.get("referer")
    if referer and "dashboard" in referer:
        return RedirectResponse(url="/admin/dashboard?tab=bookings", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/bookings", status_code=status.HTTP_303_SEE_OTHER)

# ----------------- TRACKING STAGES MANAGEMENT -----------------

@router.get("/tracking", response_class=HTMLResponse)
async def admin_tracking_list(request: Request, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.vin, v.cover_image,
               (SELECT COUNT(*) FROM tracking_stages ts WHERE ts.booking_id = b.id AND ts.status = 'completed') as completed_stages,
               (SELECT stage_title_ar FROM tracking_stages ts WHERE ts.booking_id = b.id AND ts.status = 'in_progress' LIMIT 1) as current_stage_name
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        WHERE b.status IN ('approved', 'active_tracking', 'completed')
        ORDER BY b.id DESC
    """)
    tracked_orders = cursor.fetchall()
    conn.close()

    return render_template(
        request,
        "admin/tracking_manager.html",
        {
            "admin": admin,
            "tracked_orders": tracked_orders
        }
    )

@router.get("/tracking/{booking_id}", response_class=HTMLResponse)
async def admin_tracking_detail(
    request: Request,
    booking_id: int,
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.vin, v.cover_image, v.selling_price_egp, v.country_of_origin
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        WHERE b.id = ?
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    cursor.execute("""
        SELECT * FROM tracking_stages WHERE booking_id = ? ORDER BY stage_number ASC
    """, (booking_id,))
    stages = cursor.fetchall()
    conn.close()

    # Parse JSON proof media for each stage
    parsed_stages = []
    for s in stages:
        s_dict = dict(s)
        try:
            s_dict["proof_media_list"] = json.loads(s_dict.get("proof_media") or "[]")
        except Exception:
            s_dict["proof_media_list"] = []
        parsed_stages.append(s_dict)

    return render_template(
        request,
        "admin/tracking_stage_edit.html",
        {
            "admin": admin,
            "booking": booking,
            "stages": parsed_stages
        }
    )

@router.post("/tracking/{stage_id}/update")
async def admin_update_stage_submit(
    request: Request,
    stage_id: int,
    status_val: str = Form(...),
    location: str = Form(""),
    notes: str = Form(""),
    completed_at: str = Form(""),
    proof_media_json: str = Form("[]"),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # If completed and no completed_at provided, use current timestamp
    if status_val == "completed" and not completed_at:
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("""
        UPDATE tracking_stages SET
            status = ?, location = ?, notes = ?, completed_at = ?, proof_media = ?
        WHERE id = ?
    """, (status_val, location, notes, completed_at, proof_media_json, stage_id))

    cursor.execute("SELECT booking_id FROM tracking_stages WHERE id = ?", (stage_id,))
    row = cursor.fetchone()
    booking_id = row["booking_id"] if row else 1

    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/admin/tracking/{booking_id}", status_code=status.HTTP_303_SEE_OTHER)

# ----------------- SETTINGS MANAGEMENT -----------------

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings_page(request: Request, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM settings")
    settings_rows = cursor.fetchall()
    settings = {row["key"]: row["value"] for row in settings_rows}
    conn.close()

    return render_template(
        request,
        "admin/settings.html",
        {
            "admin": admin,
            "settings": settings,
            "success_msg": None
        }
    )

@router.post("/settings", response_class=HTMLResponse)
async def admin_settings_save(
    request: Request,
    phone_primary: str = Form(...),
    phone_secondary: str = Form(""),
    whatsapp_number: str = Form(...),
    email_contact: str = Form(...),
    cairo_showroom_address_ar: str = Form(...),
    cairo_showroom_address_en: str = Form(...),
    working_hours_ar: str = Form(...),
    working_hours_en: str = Form(...),
    deposit_policy_ar: str = Form(...),
    deposit_policy_en: str = Form(...),
    admin_new_password: Optional[str] = Form(None),
    admin: dict = Depends(require_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    data = {
        "phone_primary": phone_primary,
        "phone_secondary": phone_secondary,
        "whatsapp_number": whatsapp_number,
        "email_contact": email_contact,
        "cairo_showroom_address_ar": cairo_showroom_address_ar,
        "cairo_showroom_address_en": cairo_showroom_address_en,
        "working_hours_ar": working_hours_ar,
        "working_hours_en": working_hours_en,
        "deposit_policy_ar": deposit_policy_ar,
        "deposit_policy_en": deposit_policy_en,
    }

    for k, v in data.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))

    if admin_new_password and len(admin_new_password.strip()) >= 6:
        new_hash = hash_password(admin_new_password.strip())
        cursor.execute("UPDATE admin_users SET password_hash = ? WHERE id = ?", (new_hash, admin["user_id"]))

    conn.commit()

    referer = request.headers.get("referer")
    if referer and "dashboard" in referer:
        conn.close()
        return RedirectResponse(url="/admin/dashboard?tab=settings&saved=1", status_code=status.HTTP_303_SEE_OTHER)

    cursor.execute("SELECT key, value FROM settings")
    settings_rows = cursor.fetchall()
    settings = {row["key"]: row["value"] for row in settings_rows}
    conn.close()

    return render_template(
        request,
        "admin/settings.html",
        {
            "admin": admin,
            "settings": settings,
            "success_msg": "تم حفظ الإعدادات بنجاح / Settings saved successfully!"
        }
    )
