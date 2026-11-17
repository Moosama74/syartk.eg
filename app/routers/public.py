import os
import json
import random
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.database import get_db_connection
from app.templates import render_template
from app.auth import (
    hash_password,
    verify_password,
    create_customer_token,
    get_current_user,
    require_user
)

router = APIRouter(tags=["Public Showcase"])

def get_site_settings(conn):
    """Fetch settings dictionary."""
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    return {r["key"]: r["value"] for r in rows}

def get_current_lang(request: Request) -> str:
    """Get active language from cookie, default to Arabic ('ar')."""
    return request.cookies.get("motora_lang", "ar")

@router.get("/set-lang/{lang_code}")
async def set_language(request: Request, lang_code: str):
    """Switch language and redirect back to referring page."""
    lang = "en" if lang_code == "en" else "ar"
    referer = request.headers.get("referer") or "/"
    response = RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="motora_lang", value=lang, max_age=86400 * 365, samesite="lax")
    return response

# ----------------- HOMEPAGE -----------------

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    # Featured vehicles
    cursor.execute("""
        SELECT * FROM vehicles
        WHERE status != 'hidden' AND is_featured = 1
        ORDER BY id DESC LIMIT 6
    """)
    featured_vehicles = cursor.fetchall()

    # Latest arrivals
    cursor.execute("""
        SELECT * FROM vehicles
        WHERE status != 'hidden'
        ORDER BY id DESC LIMIT 8
    """)
    latest_vehicles = cursor.fetchall()

    # Special offers
    cursor.execute("""
        SELECT * FROM vehicles
        WHERE status != 'hidden' AND is_special_offer = 1
        ORDER BY id DESC LIMIT 4
    """)
    special_offers = cursor.fetchall()

    # Brands count
    cursor.execute("""
        SELECT brand, COUNT(*) as count, cover_image
        FROM vehicles
        WHERE status != 'hidden'
        GROUP BY brand
        ORDER BY count DESC
    """)
    brands = cursor.fetchall()

    # Testimonials
    cursor.execute("""
        SELECT * FROM testimonials WHERE is_approved = 1 ORDER BY id DESC LIMIT 4
    """)
    testimonials = cursor.fetchall()

    # Total counts for trust counters
    cursor.execute("SELECT COUNT(*) as total FROM vehicles WHERE status != 'hidden'")
    total_inventory = cursor.fetchone()["total"]

    conn.close()

    return render_template(
        request,
        "index.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request),
            "featured_vehicles": featured_vehicles,
            "latest_vehicles": latest_vehicles,
            "special_offers": special_offers,
            "brands": brands,
            "testimonials": testimonials,
            "total_inventory": total_inventory
        }
    )

# ----------------- VEHICLES CATALOG -----------------

@router.get("/vehicles", response_class=HTMLResponse)
async def inventory_page(
    request: Request,
    brand: Optional[str] = None,
    origin: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    budget: Optional[str] = None,
    fuel: Optional[str] = None,
    transmission: Optional[str] = None,
    sort: Optional[str] = "newest",
    q: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    query = "SELECT * FROM vehicles WHERE status != 'hidden'"
    params = []

    if brand:
        query += " AND brand = ?"
        params.append(brand)

    if origin:
        query += " AND country_of_origin LIKE ?"
        params.append(f"%{origin}%")

    if budget:
        if budget == "under_3m":
            query += " AND selling_price_egp < 3000000"
        elif budget == "3m_6m":
            query += " AND selling_price_egp >= 3000000 AND selling_price_egp <= 6000000"
        elif budget == "6m_10m":
            query += " AND selling_price_egp >= 6000000 AND selling_price_egp <= 10000000"
        elif budget == "above_10m":
            query += " AND selling_price_egp > 10000000"

    if min_price:
        query += " AND selling_price_egp >= ?"
        params.append(min_price)

    if max_price:
        query += " AND selling_price_egp <= ?"
        params.append(max_price)

    if fuel:
        query += " AND fuel_type LIKE ?"
        params.append(f"%{fuel}%")

    if transmission:
        query += " AND transmission LIKE ?"
        params.append(f"%{transmission}%")

    if q:
        query += " AND (brand LIKE ? OR model LIKE ? OR trim LIKE ? OR country_of_origin LIKE ? OR description_ar LIKE ?)"
        s = f"%{q}%"
        params.extend([s, s, s, s, s])

    # Sorting
    if sort == "price_asc":
        query += " ORDER BY selling_price_egp ASC"
    elif sort == "price_desc":
        query += " ORDER BY selling_price_egp DESC"
    elif sort == "mileage_asc":
        query += " ORDER BY mileage ASC"
    elif sort == "year_desc":
        query += " ORDER BY year DESC, id DESC"
    else:
        query += " ORDER BY id DESC"

    cursor.execute(query, params)
    vehicles = cursor.fetchall()

    # Get distinct brands and origins for filter dropdowns
    cursor.execute("SELECT DISTINCT brand FROM vehicles WHERE status != 'hidden' ORDER BY brand ASC")
    all_brands = [r["brand"] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT country_of_origin FROM vehicles WHERE status != 'hidden' ORDER BY country_of_origin ASC")
    all_origins = [r["country_of_origin"] for r in cursor.fetchall()]

    conn.close()

    return render_template(
        request,
        "inventory.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request),
            "vehicles": vehicles,
            "all_brands": all_brands,
            "all_origins": all_origins,
            "selected_brand": brand,
            "selected_origin": origin,
            "selected_budget": budget,
            "selected_sort": sort,
            "search_query": q or ""
        }
    )

# ----------------- VEHICLE DETAIL PAGE -----------------

@router.get("/vehicle/{slug}", response_class=HTMLResponse)
async def vehicle_detail_page(request: Request, slug: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    cursor.execute("SELECT * FROM vehicles WHERE slug = ?", (slug,))
    vehicle = cursor.fetchone()

    if not vehicle:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Fetch media
    cursor.execute("SELECT * FROM vehicle_media WHERE vehicle_id = ? ORDER BY display_order ASC", (vehicle["id"],))
    media_items = cursor.fetchall()

    # Parse technical specs JSON
    specs_dict = {}
    try:
        specs_dict = json.loads(vehicle["technical_specs"] or "{}")
    except Exception:
        specs_dict = {}

    # Fetch similar vehicles (same brand or price range)
    cursor.execute("""
        SELECT * FROM vehicles
        WHERE id != ? AND status != 'hidden' AND (brand = ? OR ABS(selling_price_egp - ?) < 3000000)
        ORDER BY id DESC LIMIT 3
    """, (vehicle["id"], vehicle["brand"], vehicle["selling_price_egp"]))
    similar_vehicles = cursor.fetchall()

    conn.close()

    return render_template(
        request,
        "vehicle_detail.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request),
            "vehicle": vehicle,
            "media_items": media_items,
            "specs_dict": specs_dict,
            "similar_vehicles": similar_vehicles
        }
    )

# ----------------- CUSTOMER RESERVATION -----------------

@router.post("/api/reserve")
async def submit_reservation(
    request: Request,
    vehicle_id: int = Form(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_email: Optional[str] = Form(""),
    customer_city: Optional[str] = Form(""),
    customer_notes: Optional[str] = Form("")
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
    vehicle = cursor.fetchone()

    if not vehicle:
        conn.close()
        return JSONResponse({"success": False, "message": "السيارة المطلوبة غير موجودة / Vehicle not found"}, status_code=404)

    if vehicle["status"] == "sold" or vehicle["units_available"] <= 0:
        conn.close()
        return JSONResponse({
            "success": False,
            "message": "عذراً، هذه السيارة تم بيعها أو حجز كافة الوحدات المتاحة منها. تواصل معنا للاستيراد المباشر."
        }, status_code=400)

    # Check if customer is logged in
    user = get_current_user(request)
    user_id = user["user_id"] if user else None

    # Generate unique booking reference e.g. SYR-2026-9482
    rand_code = random.randint(1000, 9999)
    booking_code = f"SYR-2026-{rand_code}"

    # Ensure uniqueness
    cursor.execute("SELECT id FROM bookings WHERE booking_code = ?", (booking_code,))
    if cursor.fetchone():
        booking_code = f"SYR-2026-{random.randint(10000, 99999)}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    email_clean = customer_email.strip() if customer_email else (user.get("email") if user else None)
    name_clean = customer_name.strip() if customer_name else (user.get("name") if user else "")

    cursor.execute("""
        INSERT INTO bookings (
            booking_code, vehicle_id, customer_name, customer_phone, customer_email,
            customer_city, customer_notes, status, deposit_paid, deposit_amount,
            created_at, updated_at, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?)
    """, (
        booking_code, vehicle_id, name_clean, customer_phone.strip(),
        email_clean,
        customer_city.strip() if customer_city else "مدينة العبور - القاهرة",
        customer_notes.strip() if customer_notes else None,
        vehicle["reservation_deposit_egp"] or 0,
        now, now, user_id
    ))
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return JSONResponse({
        "success": True,
        "booking_code": booking_code,
        "booking_id": booking_id,
        "tracking_url": f"/tracking/{booking_code}",
        "message": f"تم استلام طلب الحجز بنجاح! كود الحجز والمتابعة الخاص بك هو: {booking_code}"
    })

# ----------------- CUSTOMER AUTHENTICATION (REGISTER / LOGIN / PROFILE) -----------------

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    conn = get_db_connection()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)
    conn.close()
    return render_template(request, "register.html", {
        "lang": lang,
        "settings": settings,
        "user": None,
        "error": None
    })

@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    city: str = Form("مدينة العبور - القاهرة")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    email_clean = email.strip().lower()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
    if cursor.fetchone():
        conn.close()
        return render_template(request, "register.html", {
            "lang": lang,
            "settings": settings,
            "user": None,
            "error": "هذا البريد الإلكتروني مسجل لدينا بالفعل، يرجى تسجيل الدخول أو استخدام بريد آخر."
        }, status_code=400)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p_hash = hash_password(password)

    cursor.execute("""
        INSERT INTO users (name, email, phone, password_hash, city, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name.strip(), email_clean, phone.strip(), p_hash, city.strip(), now))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    token = create_customer_token(user_id, email_clean, name.strip())
    response = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="syartk_user_session", value=token, max_age=86400 * 30, httponly=True, samesite="lax")
    return response

@router.get("/login", response_class=HTMLResponse)
async def customer_login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    conn = get_db_connection()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)
    conn.close()
    return render_template(request, "login.html", {
        "lang": lang,
        "settings": settings,
        "user": None,
        "error": None,
        "success_msg": None
    })

@router.post("/login", response_class=HTMLResponse)
async def customer_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    email_clean = email.strip().lower()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        return render_template(request, "login.html", {
            "lang": lang,
            "settings": settings,
            "user": None,
            "error": "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
            "success_msg": None
        }, status_code=400)

    token = create_customer_token(user["id"], user["email"], user["name"])
    response = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="syartk_user_session", value=token, max_age=86400 * 30, httponly=True, samesite="lax")
    return response

@router.get("/logout")
async def customer_logout_submit():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("syartk_user_session")
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user_payload = get_current_user(request)
    if not user_payload:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_payload["user_id"],))
    user = cursor.fetchone()

    if not user:
        conn.close()
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie("syartk_user_session")
        return response

    # Fetch user's bookings with vehicle info
    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.slug, v.vin, v.cover_image, v.selling_price_egp, v.country_of_origin
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        WHERE b.user_id = ? OR b.customer_email = ? OR b.customer_phone = ?
        ORDER BY b.id DESC
    """, (user["id"], user["email"], user["phone"]))
    bookings = cursor.fetchall()
    conn.close()

    return render_template(request, "profile.html", {
        "lang": lang,
        "settings": settings,
        "user": user,
        "bookings": bookings
    })

# ----------------- VEHICLE TRACKING SYSTEM -----------------

@router.get("/tracking", response_class=HTMLResponse)
async def tracking_search_page(
    request: Request,
    code: Optional[str] = Query(None)
):
    if code and code.strip():
        return RedirectResponse(url=f"/tracking/{code.strip()}", status_code=status.HTTP_303_SEE_OTHER)

    conn = get_db_connection()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)
    conn.close()

    return render_template(
        request,
        "tracking.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request),
            "booking": None,
            "stages": [],
            "error_msg": None
        }
    )

@router.get("/tracking/{booking_code}", response_class=HTMLResponse)
async def tracking_detail_page(request: Request, booking_code: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)

    # Search by booking code or phone number
    cursor.execute("""
        SELECT b.*, v.brand, v.model, v.year, v.trim, v.vin, v.country_of_origin,
               v.cover_image, v.selling_price_egp, v.expected_delivery_time
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        WHERE UPPER(b.booking_code) = UPPER(?) OR b.customer_phone = ?
        ORDER BY b.id DESC LIMIT 1
    """, (booking_code.strip(), booking_code.strip()))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return render_template(
            request,
            "tracking.html",
            {
                "lang": lang,
                "settings": settings,
                "booking": None,
                "stages": [],
                "searched_code": booking_code,
                "error_msg": "لم يتم العثور على أي حجز مطابق لكود المتابعة أو رقم الهاتف المدخل. يرجى التأكد من الكود أو التواصل مع خدمة عملاء سيارتك."
            }
        )

    # Fetch stages
    cursor.execute("""
        SELECT * FROM tracking_stages WHERE booking_id = ? ORDER BY stage_number ASC
    """, (booking["id"],))
    stages_rows = cursor.fetchall()
    conn.close()

    # Parse proof media JSON
    stages = []
    completed_count = 0
    for s in stages_rows:
        s_dict = dict(s)
        try:
            s_dict["proof_media_list"] = json.loads(s_dict.get("proof_media") or "[]")
        except Exception:
            s_dict["proof_media_list"] = []
        if s_dict["status"] == "completed":
            completed_count += 1
        stages.append(s_dict)

    progress_percent = int((completed_count / 9) * 100) if stages else 15

    return render_template(
        request,
        "tracking.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request),
            "booking": booking,
            "stages": stages,
            "completed_count": completed_count,
            "progress_percent": progress_percent,
            "searched_code": booking_code,
            "error_msg": None
        }
    )

# ----------------- INFORMATIONAL PAGES -----------------

@router.get("/how-it-works", response_class=HTMLResponse)
async def how_it_works_page(request: Request):
    conn = get_db_connection()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)
    conn.close()

    return render_template(
        request,
        "how_it_works.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request)
        }
    )

@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    conn = get_db_connection()
    settings = get_site_settings(conn)
    lang = get_current_lang(request)
    conn.close()

    return render_template(
        request,
        "contact.html",
        {
            "lang": lang,
            "settings": settings,
            "user": get_current_user(request)
        }
    )
