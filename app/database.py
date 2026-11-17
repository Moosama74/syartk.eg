import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "motora.db")

def get_db_connection() -> sqlite3.Connection:
    """Create a connection with dict row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database tables and seed initial data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Admin Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT DEFAULT 'owner',
        created_at TEXT NOT NULL
    );
    """)

    # 2. Vehicles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        year INTEGER NOT NULL,
        trim TEXT,
        country_of_origin TEXT NOT NULL,
        engine_capacity TEXT,
        fuel_type TEXT NOT NULL,
        transmission TEXT NOT NULL,
        mileage INTEGER NOT NULL DEFAULT 0,
        exterior_color TEXT NOT NULL,
        interior_color TEXT NOT NULL,
        vehicle_condition TEXT NOT NULL,
        vin TEXT UNIQUE NOT NULL,
        units_available INTEGER NOT NULL DEFAULT 1,
        units_total INTEGER NOT NULL DEFAULT 1,
        selling_price_egp REAL NOT NULL,
        reservation_deposit_egp REAL NOT NULL DEFAULT 0,
        expected_delivery_time TEXT NOT NULL,
        description_ar TEXT,
        description_en TEXT,
        technical_specs TEXT,
        additional_notes TEXT,
        status TEXT NOT NULL DEFAULT 'available',
        is_featured INTEGER DEFAULT 0,
        is_latest INTEGER DEFAULT 1,
        is_special_offer INTEGER DEFAULT 0,
        cover_image TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 3. Vehicle Media Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        media_type TEXT NOT NULL DEFAULT 'image',
        url TEXT NOT NULL,
        caption TEXT,
        display_order INTEGER NOT NULL DEFAULT 0,
        is_cover INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
    );
    """)

    # 4. Bookings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        vehicle_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_email TEXT,
        customer_city TEXT,
        customer_notes TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        deposit_paid INTEGER NOT NULL DEFAULT 0,
        deposit_amount REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT
    );
    """)

    # 5. Tracking Stages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tracking_stages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        stage_number INTEGER NOT NULL,
        stage_title_ar TEXT NOT NULL,
        stage_title_en TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        completed_at TEXT,
        location TEXT,
        notes TEXT,
        proof_media TEXT,
        FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    );
    """)

    # 6. Testimonials Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS testimonials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        city TEXT NOT NULL,
        vehicle_purchased TEXT NOT NULL,
        rating INTEGER NOT NULL DEFAULT 5,
        comment_ar TEXT NOT NULL,
        comment_en TEXT NOT NULL,
        avatar_url TEXT,
        date_text TEXT,
        is_approved INTEGER NOT NULL DEFAULT 1
    );
    """)

    # 7. Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # 8. Customer Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        city TEXT DEFAULT 'مدينة العبور - القاهرة',
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

    # Seed initial data
    seed_database_if_empty()

def seed_database_if_empty():
    """Populate default admin, luxury fleet, settings, and sample tracking."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if admin exists
    cursor.execute("SELECT COUNT(*) as cnt FROM admin_users")
    if cursor.fetchone()['cnt'] == 0:
        from app.auth import hash_password
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        admin_pass = hash_password("motora2026admin")
        cursor.execute("""
            INSERT INTO admin_users (username, password_hash, full_name, email, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", admin_pass, "مدير صالة سيارتك - SYARTK Showroom Owner", "owner@motora.eg", "owner", now))

    # Check settings
    cursor.execute("SELECT COUNT(*) as cnt FROM settings")
    if cursor.fetchone()['cnt'] == 0:
        default_settings = {
            "site_name_ar": "Syartk",
            "site_name_en": "Syartk",
            "tagline_ar": "Syartk - المنصة الحصرية لاستيراد وتوريد السيارات الفاخرة | مدينة العبور - القاهرة",
            "tagline_en": "Syartk - Exclusive Luxury Automotive Import Platform | El Obour City - Cairo",
            "phone_primary": "01125626292",
            "phone_secondary": "01125626292",
            "whatsapp_number": "201125626292",
            "email_contact": "contact@syartk.com",
            "cairo_showroom_address_ar": "مدينة العبور - القاهرة (صالة عرض Syartk)",
            "cairo_showroom_address_en": "El Obour City - Cairo (Syartk Showroom)",
            "working_hours_ar": "السبت إلى الخميس: 10:00 ص - 10:00 م | الجمعة: 2:00 م - 10:00 م",
            "working_hours_en": "Saturday to Thursday: 10:00 AM - 10:00 PM | Friday: 2:00 PM - 10:00 PM",
            "deposit_policy_ar": "عربون الجدية يسدد عبر الحساب البنكي أو إنستاباي ويخصم بالكامل من سعر السيارة عند التعاقد.",
            "deposit_policy_en": "Booking deposit is processed via official bank transfer or InstaPay, 100% credited toward vehicle total upon contract."
        }
        for k, v in default_settings.items():
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Check vehicles
    cursor.execute("SELECT COUNT(*) as cnt FROM vehicles")
    if cursor.fetchone()['cnt'] == 0:
        seed_vehicles_data(conn)

    # Check testimonials
    cursor.execute("SELECT COUNT(*) as cnt FROM testimonials")
    if cursor.fetchone()['cnt'] == 0:
        testimonials = [
            (
                "المهندس طارق السلاب",
                "القاهرة - الشيخ زايد",
                "Mercedes-Benz G63 AMG 2024",
                5,
                "تجربة استيراد استثنائية لم أعش مثلها في مصر. الدقة في المواعيد، وفحص الفابريكة في ألمانيا بالفيديو عالي الدقة، ونظام التتبع لحظة بلحظة كان مذهلاً. السيارة وصلت كما وُعدت تماماً.",
                "An exceptional import experience unlike anything in Egypt. Precise timeline, high-definition inspection video from Germany, and live tracking every step. Vehicle arrived immaculate.",
                "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80",
                "أكتوبر 2026"
            ),
            (
                "د. كريم الشرقاوي",
                "الإسكندرية - سموحة",
                "Porsche 911 Carrera 4S 2023",
                5,
                "كنت متخوفاً من إجراءات الجمارك والشحن، لكن فريق سيارتك تولى كل شيء بالكامل باحترافية وأوراق رسمية معتمدة. استلمت البورش بأوراقها وفحصها المروري في وقت قياسي.",
                "I was worried about Egyptian customs and shipping procedures, but SYARTK handled everything seamlessly with certified documents. Received my 911 in record time.",
                "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&q=80",
                "سبتمبر 2026"
            ),
            (
                "أ/ ياسين عبد العزيز",
                "القاهرة الجديدة - التجمع الخامس",
                "Hyundai Tucson 1.6T N-Line 2024",
                5,
                "استوردت توسان N-Line من كوريا الجنوبية بأعلى فئة مواصفات غير متوفرة في السوق المحلي وبسعر منافس جداً مقارنة بالوكيل. المتابعة اليومية عبر كود التتبع أراحتني تماماً.",
                "Imported a Tucson N-Line directly from South Korea with highest specs unavailable locally at a very competitive price. Daily tracking updates gave me complete peace of mind.",
                "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80",
                "أغسطس 2026"
            )
        ]
        for t in testimonials:
            cursor.execute("""
                INSERT INTO testimonials (client_name, city, vehicle_purchased, rating, comment_ar, comment_en, avatar_url, date_text, is_approved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, t)

    conn.commit()
    conn.close()

def seed_vehicles_data(conn: sqlite3.Connection):
    """Seed comprehensive initial fleet of imported luxury and high-demand vehicles."""
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    vehicles_list = [
        {
            "slug": "mercedes-amg-g63-2024-night-edition",
            "brand": "Mercedes-Benz",
            "model": "G-Class AMG G63",
            "year": 2024,
            "trim": "Night Package II Exclusive",
            "country_of_origin": "Germany",
            "engine_capacity": "4.0L V8 BiTurbo (577 HP)",
            "fuel_type": "بنزين (Petrol)",
            "transmission": "أوتوماتيك AMG SPEEDSHIFT PLUS 9G-TRONIC",
            "mileage": 4200,
            "exterior_color": "أسود نايت ماجنو ميتاليك (Obsidian Black Magno)",
            "interior_color": "جلد نابا أحمر بنغالي مع كربون فايبر (Bengal Red Nappa)",
            "vehicle_condition": "فابريكة بالكامل - حالة المصنع (Pristine Condition)",
            "vin": "WDB4632761X894120",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 12850000,
            "reservation_deposit_egp": 400000,
            "expected_delivery_time": "15 - 20 يوم عمل شامل الإفراج الجمركي",
            "description_ar": "أيقونة الطرق الوعرة والفخامة المطلقة. مرسيدس G63 AMG موديل 2024 وارد ألمانيا مباشرة من صالات شتوتغارت المعتمدة. حزمة النايت باكج الكاملة مع جنوط أصلية مقاس 22 بوصة فورجد، نظام عادم رياضي بصوت مهيب مع تحكم بالصمامات، كاميرات 360، نظام صوتي فاخر Burmester 3D، شاشات خلفية، مقاعد تدليك وتهوية.",
            "description_en": "The absolute pinnacle of luxury SUV engineering. 2024 Mercedes-AMG G63 directly imported from certified German showrooms in Stuttgart. Full Night Package II with 22-inch forged AMG cross-spoke wheels, active valve AMG performance exhaust, Burmester 3D Surround Sound, dynamic massage seats, and carbon fiber interior trim.",
            "technical_specs": json.dumps({
                "الأداء والمحرك": {
                    "المحرك": "4.0 لتر V8 توين تيربو يدوي الصنع (Handcrafted AMG)",
                    "القوة الحصانية": "577 حصان @ 6000 دورة/دقيقة",
                    "عزم الدوران": "850 نيوتن.متر",
                    "التسارع 0-100 كم/س": "4.5 ثوانٍ فقط",
                    "السرعة القصوى": "240 كم/س (AMG Driver's Package)",
                    "نظام الدفع": "دفع كلي مستمر 4MATIC مع 3 أقفال تفاضلية كاملة"
                },
                "المقصورة والرفاهية": {
                    "الفرش الداخلي": "جلد نابا أحمر فاخر مع خياطة ماسية دقيقة",
                    "النظام الصوتي": "Burmester High-End 3D Surround Sound بـ 15 سماعة",
                    "الشاشات": "شاشتان عريضتان 12.3 بوصة بدقة 4K مع نظام MBUX المتطور",
                    "المقاعد": "مقاعد كهربائية بـ 16 اتجاه مع ذاكرة، تدليك، تبريد وتدفئة",
                    "الإضاءة": "إضاءة محيطية تفاعلية بـ 64 لوناً"
                },
                "السلامة ومساعدة السائق": {
                    "أنظمة القيادة الذاتية": "رادار تفاعلي DISTRONIC، الحفاظ على المسار، فرامل الطوارئ الذاتية",
                    "الرؤية": "كاميرات محيطية 360 درجة مع حساسات فائقة الدقة",
                    "المصابيح": "MULTIBEAM LED مع مساعد الضوء العالي المتكيف"
                }
            }, ensure_ascii=False),
            "additional_notes": "السيارة خالية تماماً من أي حوادث أو دهانات (Clean CarFax & Dekra Certified). جاهزة للشحن الفوري إلى ميناء الإسكندرية مع وثائق الضمان الدولي وشهادة اليورو 1.",
            "status": "available",
            "is_featured": 1,
            "is_latest": 1,
            "is_special_offer": 1,
            "cover_image": "https://images.unsplash.com/photo-1520031441872-265e4ff70366?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1520031441872-265e4ff70366?auto=format&fit=crop&w=1200&q=80", "واجهة أمامية مهيبة مع شبك باناميريكانا المضيء", 1, 1),
                ("image", "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=1200&q=80", "زاوية جانبية تظهر جنوط AMG مقاس 22 بوصة", 2, 0),
                ("image", "https://images.unsplash.com/photo-1563720223185-11003d516935?auto=format&fit=crop&w=1200&q=80", "مقصورة القيادة الفاخرة المطعمة بالكربون فايبر ونظام MBUX", 3, 0),
                ("image", "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=1200&q=80", "تفاصيل المقاعد الخلفية جلد نابا أحمر بنغالي", 4, 0),
                ("video", "https://assets.mixkit.co/videos/preview/mixkit-car-driving-through-a-dark-tunnel-4171-large.mp4", "فيديو فحص السيارة التشغيلي وصوت العادم الرياضي", 5, 0)
            ]
        },
        {
            "slug": "porsche-911-carrera-4s-992-2023",
            "brand": "Porsche",
            "model": "911 Carrera 4S (992)",
            "year": 2023,
            "trim": "Sport Chrono Package",
            "country_of_origin": "Germany",
            "engine_capacity": "3.0L Twin-Turbo Flat-6 (443 HP)",
            "fuel_type": "بنزين (Petrol)",
            "transmission": "أوتوماتيك 8-Speed Porsche Doppelkupplung (PDK)",
            "mileage": 12000,
            "exterior_color": "فضي جي تي ميتاليك (GT Silver Metallic)",
            "interior_color": "جلد بوردو أحمر رياضي مع سقف ألكانتارا (Bordeaux Red Leather)",
            "vehicle_condition": "فابريكة بالكامل - صيانة توكيل معتمدة في ألمانيا",
            "vin": "WP0AB2A97PS248911",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 9450000,
            "reservation_deposit_egp": 300000,
            "expected_delivery_time": "15 - 22 يوم عمل",
            "description_ar": "الأسطورة الألمانية بورشه 911 كاريرا 4S الجيل 992. مزودة بحزمة سبورت كرونو الرياضية وسقف بانورامي زجاجي قابل للفتح. نظام العادم الرياضي الأصلي بورشه مع مخارج سوداء، ونظام رفع المحور الأمامي Front Axle Lift لتجاوز المطبات بكل سلاسة في الشوارع المصرية.",
            "description_en": "The definitive sports car. Porsche 911 Carrera 4S (992) with Sport Chrono Package and SportDesign aerodynamic package. Equipped with Porsche Dynamic Chassis Control (PDCC), Front Axle Lift system, Sport Exhaust system with black quad tips, and Bose Surround Sound.",
            "technical_specs": json.dumps({
                "الأداء والمحرك": {
                    "المحرك": "3.0 لتر 6 أسطوانات مسطحة (Boxer) توين تيربو",
                    "القوة الحصانية": "443 حصان @ 6500 دورة/دقيقة",
                    "عزم الدوران": "530 نيوتن.متر",
                    "التسارع 0-100 كم/س": "3.4 ثوانٍ مع Launch Control",
                    "السرعة القصوى": "306 كم/س",
                    "نظام الدفع": "دفع كلي ذكي AWD مع نظام بورشه للتحكم في الجر (PTM)"
                },
                "التجهيزات الخاصة": {
                    "حزمة الرياضة": "Sport Chrono Package مع ساعة التوقيت التناظرية/الرقمية",
                    "نظام الرفع": "Front Axle Lift System لرفع مقدمة السيارة 40 مم",
                    "العادم": "نظام عادم بورشه الرياضي المزدوج القابل للتحكم",
                    "الصوت": "BOSE Surround Sound System 12 مكبر صوت"
                }
            }, ensure_ascii=False),
            "additional_notes": "تقرير فحص Dekra الألماني متاح بالكامل (111 نقطة فحص رسمية من بورشه معتمدة).",
            "status": "available",
            "is_featured": 1,
            "is_latest": 1,
            "is_special_offer": 0,
            "cover_image": "https://images.unsplash.com/photo-1614162692292-7ac56d7f7f1e?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1614162692292-7ac56d7f7f1e?auto=format&fit=crop&w=1200&q=80", "المظهر الرياضي الخارق لبورشه 911 كاريرا 4S", 1, 1),
                ("image", "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80", "الخطوط الخلفية الشهيرة وشريط الإضاءة LED المتصل", 2, 0),
                ("image", "https://images.unsplash.com/photo-1580273916550-e323be2ae537?auto=format&fit=crop&w=1200&q=80", "المقصورة والعدادات الرقمية مع حزمة سبورت كرونو", 3, 0)
            ]
        },
        {
            "slug": "bmw-x7-m60i-xdrive-2024",
            "brand": "BMW",
            "model": "X7 M60i xDrive",
            "year": 2024,
            "trim": "M Sport Pro Package",
            "country_of_origin": "Germany",
            "engine_capacity": "4.4L BMW M TwinPower Turbo V8 (523 HP)",
            "fuel_type": "بنزين (Mild Hybrid 48V)",
            "transmission": "أوتوماتيك 8-Speed Steptronic Sport",
            "mileage": 8500,
            "exterior_color": "أبيض مينيرال ميتاليك (Mineral White Metallic)",
            "interior_color": "جلد تارتوفو ميرينو كامل (Tartufo Full Merino Leather)",
            "vehicle_condition": "كسر زيرو - صيانة بي إم دابليو الرسمية (Like New)",
            "vin": "5UXCW8C03R9P71024",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 8900000,
            "reservation_deposit_egp": 250000,
            "expected_delivery_time": "14 - 20 يوم عمل",
            "description_ar": "قمة فخامة السيارات الرياضية متعددة الاستخدامات 7 مقاعد. بي إم دابليو X7 M60i موديل 2024 بمحرك 8 أسطوانات جبار مع تقنية مايلد هايبريد. سقف بانوراما Sky Lounge مع إضاءة نجوم LED مدمجة، شاشة BMW Curved Display العملاقة، أبواب شفط Soft-Close، نظام تعليق هوائي متكيف، وجنوط 23 بوصة M Sport.",
            "description_en": "The flagship luxury 7-passenger SAV. 2024 BMW X7 M60i xDrive powered by a twin-turbo 4.4L V8 with 48V mild hybrid assistance. Features Sky Lounge Panoramic LED Roof, Bowers & Wilkins Diamond Surround Sound, rear entertainment, and 2-axle air suspension.",
            "technical_specs": json.dumps({
                "الأداء والمحرك": {
                    "المحرك": "4.4 لتر V8 M TwinPower Turbo بتكنولوجيا Mild Hybrid",
                    "القوة الحصانية": "523 حصان",
                    "عزم الدوران": "750 نيوتن.متر",
                    "التسارع 0-100 كم/س": "4.7 ثوانٍ",
                    "نظام التعليق": "نظام تعليق هوائي متكيف ثنائي المحور Executive Drive Pro"
                },
                "الراحة والتقنيات": {
                    "السقف": "بانوراما Sky Lounge المضيء بآلاف نقاط الإضاءة",
                    "المقاعد": "7 مقاعد كهربائية بالكامل مع تدفئة وتبريد وتدليك بالصف الأول والثاني",
                    "الصوت": "Bowers & Wilkins Diamond Surround بـ 20 مكبر صوت",
                    "الشاشات": "شاشة منحنية موحدة 14.9 بوصة لنظام iDrive 8.5 مع نظام الملاحة بالواقع المعزز"
                }
            }, ensure_ascii=False),
            "additional_notes": "وارد ألمانيا مع ضمان دولي وتقرير شامل لجميع الأنظمة الإلكترونية والميكانيكية.",
            "status": "available",
            "is_featured": 1,
            "is_latest": 1,
            "is_special_offer": 0,
            "cover_image": "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1200&q=80", "الإطلالة الفاخرة للواجهة المحدثة لـ BMW X7 M60i", 1, 1),
                ("image", "https://images.unsplash.com/photo-1556189250-72ba954cfc2b?auto=format&fit=crop&w=1200&q=80", "تفاصيل المقصورة الفارهة والشاشة المنحنية الموحدة", 2, 0),
                ("image", "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=1200&q=80", "المقاعد الجلدية ميرينو والتطريزات الماسية", 3, 0)
            ]
        },
        {
            "slug": "hyundai-tucson-16t-nline-2024",
            "brand": "Hyundai",
            "model": "Tucson 1.6T",
            "year": 2024,
            "trim": "N-Line Edition (Full Spec)",
            "country_of_origin": "South Korea",
            "engine_capacity": "1.6L SmartStream T-GDI Turbo (180 HP)",
            "fuel_type": "بنزين (Petrol)",
            "transmission": "أوتوماتيك 7-Speed Dual Clutch (DCT)",
            "mileage": 6800,
            "exterior_color": "رمادي شادو جراي الرياضي (Shadow Grey N-Line)",
            "interior_color": "ألكانتارا رياضي أسود مع خياطة حمراء N-Line",
            "vehicle_condition": "فابريكة بالكامل - استيراد مباشر من كوريا الجنوبية",
            "vin": "KM8JN81B6RU109281",
            "units_available": 2,
            "units_total": 2,
            "selling_price_egp": 2150000,
            "reservation_deposit_egp": 80000,
            "expected_delivery_time": "20 - 28 يوم عمل",
            "description_ar": "هيونداي توسان وارد كوريا الجنوبية بمواصفات الفخامة والرياضة الكاملة N-Line. مجهزة بحزمة الأمان المتطورة Hyundai SmartSense، كاميرات 360 رؤية محيطية، شاشات رقمية مزدوجة 10.25 بوصة، فتحة سقف بانورامية، تبريد وتدفئة المقاعد وعجلة القيادة، وشنطة كهربائية ذكية.",
            "description_en": "Directly imported from South Korea, 2024 Hyundai Tucson 1.6T N-Line. Full European/Korean specification with ADAS Level 2 safety suite, surround-view monitors, panoramic sunroof, ventilated leather/Alcantara sports seats, and shift-by-wire controls.",
            "technical_specs": json.dumps({
                "المحرك والأداء": {
                    "سعة المحرك": "1.6 لتر تيربو بنظام الحقن المباشر GDI",
                    "القوة": "180 حصان",
                    "ناقل الحركة": "7 سرعات مزدوج القابض DCT مع مبدلات سرعة بالطارة",
                    "أنظمة القيادة": "Eco, Normal, Sport, Smart"
                },
                "المواصفات الكورية الحصرية": {
                    "الشاشات": "شاشة عدادات رقمية 10.25 + شاشة ملاحة 10.25 بوصة",
                    "الأمان الذكي": "مثبت سرعة ذكي متكيف رادار، مانع تصادم أمامي وخلفي، كشف النقط العمياء في العدادات",
                    "الراحة": "مقاعد أمامية مكيفة ومهواة، ذاكرة لمقعد السائق، شاحن لاسلكي سريع"
                }
            }, ensure_ascii=False),
            "additional_notes": "السيارة بأوراق الفحص الكورية الموثقة من هيئة المرور الكورية (K-Car Verified). شاملة الشحن والتخليص.",
            "status": "available",
            "is_featured": 1,
            "is_latest": 1,
            "is_special_offer": 1,
            "cover_image": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1200&q=80", "واجهة هيونداي توسان الرياضية N-Line", 1, 1),
                ("image", "https://images.unsplash.com/photo-1508974239320-0a029497e820?auto=format&fit=crop&w=1200&q=80", "التصميم الجانبي الديناميكي مع جنوط N-Line الحصرية", 2, 0)
            ]
        },
        {
            "slug": "kia-sorento-16t-hybrid-2024",
            "brand": "Kia",
            "model": "Sorento 1.6T HEV",
            "year": 2024,
            "trim": "Signature Gravity (6-Seater VIP)",
            "country_of_origin": "South Korea",
            "engine_capacity": "1.6L Turbo Hybrid HEV (230 HP)",
            "fuel_type": "هايبرد اقتصادي (Hybrid Electric)",
            "transmission": "أوتوماتيك 6-Speed Electronic Shift",
            "mileage": 9100,
            "exterior_color": "أبيض لؤلؤي سنو وايت (Snow White Pearl)",
            "interior_color": "جلد نابا بني جملي سادل براون VIP (Saddle Brown Nappa)",
            "vehicle_condition": "حالة الوكالة - فابريكة دهان المصنع بالكامل",
            "vin": "KNAND81C3R5819022",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 2750000,
            "reservation_deposit_egp": 100000,
            "expected_delivery_time": "20 - 28 يوم عمل",
            "description_ar": "كيا سورينتو الفيس ليفت موديل 2024 وارد كوريا الجنوبية بمحرك هايبرد اقتصادي وقوي للغاية. فئة 6 مقاعد كابتن VIP المنفصلة مع سقف بانوراما، شاشة بانورامية منحنية موحدة تضم أحدث نظام تشغيل لكيا، نظام صوتي بريميوم KRELL، وإضاءة محيطية تفاعلية راقية.",
            "description_en": "2024 Facelift Kia Sorento 1.6T HEV Hybrid imported directly from South Korea. Premium 6-seater configuration with individual second-row captain chairs, dual curved panoramic displays, KRELL premium sound, and ultra-efficient hybrid powertrain.",
            "technical_specs": json.dumps({
                "المحرك والاقتصاد": {
                    "منظومة الحركة": "1.6 لتر تيربو بنزين + محرك كهربائي وبطارية ليثيوم أيون",
                    "القوة الإجمالية": "230 حصان",
                    "استهلاك الوقود": "اقتصادي جداً بمعدل 18-20 كم/لتر",
                    "وضعيات القيادة": "Eco, Sport, Smart"
                },
                "فخامة الـ VIP": {
                    "المقاعد": "6 مقاعد جلد نابا أصلي مع كراسي كابتن منفصلة بالصف الثاني",
                    "الشاشات": "لوحة شاشات منحنية مزدوجة مقاس 12.3 بوصة لكل شاشة",
                    "الأنظمة الصوتية": "نظام Krell الأمريكي الفاخر بـ 12 سماعة ومضخم صوت",
                    "الزجاج": "زجاج مزدوج عازل للصوت والحرارة في جميع النوافذ"
                }
            }, ensure_ascii=False),
            "additional_notes": "السيارة حاصلة على أعلى تقييم فحص كوري (درجة ممتاز Grade A+).",
            "status": "available",
            "is_featured": 0,
            "is_latest": 1,
            "is_special_offer": 0,
            "cover_image": "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1200&q=80", "واجهة كيا سورينتو الفيس ليفت الجديدة كلياً", 1, 1),
                ("image", "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1200&q=80", "مظهر جانبي أنيق للسيارة العائلية الفاخرة", 2, 0)
            ]
        },
        {
            "slug": "range-rover-sport-dynamic-se-2024",
            "brand": "Land Rover",
            "model": "Range Rover Sport",
            "year": 2024,
            "trim": "Dynamic SE (Gulf Specs)",
            "country_of_origin": "UAE (Gulf Specs)",
            "engine_capacity": "3.0L i6 Turbo MHEV (400 HP)",
            "fuel_type": "بنزين (Petrol Mild Hybrid)",
            "transmission": "أوتوماتيك ZF 8-Speed مع وضعيات Terrain Response 2",
            "mileage": 5400,
            "exterior_color": "أسود سانتوريني ميتاليك (Santorini Black)",
            "interior_color": "جلد وندسور كاراوي تان (Caraway Windsor Leather)",
            "vehicle_condition": "تحت ضمان الوكيل في الشرق الأوسط - فابريكة تماماً",
            "vin": "SALWR2V48RA918231",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 10200000,
            "reservation_deposit_egp": 350000,
            "expected_delivery_time": "10 - 15 يوم عمل (شحن سريع من الإمارات)",
            "description_ar": "رينج روفر سبورت موديل 2024 بمواصفات خليجية ممتازة تناسب الأجواء المصرية تماماً، وارد دبي. نظام تعليق هوائي ديناميكي مع توجيه لجميع العجلات All-Wheel Steering، شاشة Pivi Pro العائمة 13.1 بوصة، نظام صوتي Meridian 3D الفاخر، عزل صوتي نشط للمقصورة، وجنوط 22 بوصة دايموند كت.",
            "description_en": "2024 Range Rover Sport Dynamic SE imported directly from Dubai with full Gulf GCC specifications. Featuring dynamic air suspension with all-wheel steering, 13.1-inch curved floating Pivi Pro touchscreen, Meridian 3D audio, and 22-inch diamond-turned rims.",
            "technical_specs": json.dumps({
                "المحرك والقيادة": {
                    "المحرك": "3.0 لتر 6 أسطوانات تيربو كهربائي مزدوج مع Mild Hybrid",
                    "القوة": "400 حصان",
                    "عزم الدوران": "550 نيوتن.متر",
                    "نظام التضاريس": "Terrain Response 2 المتكيف مع الرمال والطين والصخور",
                    "التوجيه": "توجيه المحور الخلفي الرباعي للمناورة السلسة"
                },
                "الرفاهية والتقنيات": {
                    "المقاعد": "جلد ويندسور الفاخر مع تحكم بـ 20 اتجاه ومساج وتبريد",
                    "النظام الصوتي": "Meridian 3D Surround Sound 800 واط",
                    "الأبواب": "أبواب شفط أوتوماتيكية Soft-Door Close ومقابض منبثقة متدفقة",
                    "المصابيح": "Digital LED مع شعاع متكيف ومسقاط إشارات ضوئية"
                }
            }, ensure_ascii=False),
            "additional_notes": "تتميز بمواصفات خليجية مطابقة للمناخ المصري وتبريد مكيف فائق القوة.",
            "status": "available",
            "is_featured": 1,
            "is_latest": 1,
            "is_special_offer": 0,
            "cover_image": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1200&q=80", "الإطلالة الرياضية والوقفة القوية لرينج روفر سبورت", 1, 1),
                ("image", "https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2?auto=format&fit=crop&w=1200&q=80", "التصميم العصري للمصابيح الخلفية الانسيابية", 2, 0)
            ]
        },
        {
            "slug": "genesis-gv80-35t-prestige-2024",
            "brand": "Genesis",
            "model": "GV80 3.5T AWD",
            "year": 2024,
            "trim": "Prestige Signature (Facelift)",
            "country_of_origin": "South Korea",
            "engine_capacity": "3.5L Twin-Turbo V6 (375 HP)",
            "fuel_type": "بنزين (Petrol)",
            "transmission": "أوتوماتيك 8-Speed Shift-by-Wire",
            "mileage": 7200,
            "exterior_color": "أبيض أويوني لؤلؤي (Uyuni White Pearl)",
            "interior_color": "جلد نابا أزرق أولترامارين وبيج دوني (Ultramarine & Dune Nappa)",
            "vehicle_condition": "فابريكة بالكامل - وارد كوريا الجنوبية VIP",
            "vin": "KMUGD81B8RU094182",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 4600000,
            "reservation_deposit_egp": 150000,
            "expected_delivery_time": "20 - 25 يوم عمل",
            "description_ar": "تحفة الفخامة الكورية جينيسيس GV80 الفيس ليفت الجديدة. شاشة OLED عملاقة موحدة مقاس 27 بوصة تمتد عبر لوحة القيادة، مقاعد Ergo Motion الذكية لتخفيف الإجهاد والتدليك، نظام صوتي فائق Bang & Olufsen، نظام تعليق إلكتروني يقرأ الطريق بالكاميرا الأمامية لتوفير أعلى درجات الراحة.",
            "description_en": "The crowning achievement of Korean luxury. 2024 Genesis GV80 Facelift 3.5T Prestige. Features a breathtaking 27-inch seamless OLED display, Bang & Olufsen bespoke sound system, preview electronically controlled suspension, and Ergo-Motion massage seats.",
            "technical_specs": json.dumps({
                "الأداء": {
                    "المحرك": "3.5 لتر V6 توين تيربو بنزين",
                    "القوة": "375 حصان",
                    "عزم الدوران": "530 نيوتن.متر",
                    "نظام التعليق": "تعليق ذكي بتحكم إلكتروني مع كاميرا قراءة المطبات الأمامية (Road Preview)"
                },
                "الرفاهية الحصرية": {
                    "الشاشة": "شاشة مدمجة 27 بوصة OLED بدقة فائقة 4K",
                    "الصوت": "نظام Bang & Olufsen العالمي بـ 18 سماعة مع تحكم صوتي ثلاثي الأبعاد",
                    "المقاعد": "جلد نابا أصلي مع مقاعد مساج ذكية Ergo Motion وأبواب شفط"
                }
            }, ensure_ascii=False),
            "additional_notes": "استيراد مباشر من سيول مع ضمان فحص شامل ومستندات جمركية مسجلة.",
            "status": "available",
            "is_featured": 0,
            "is_latest": 1,
            "is_special_offer": 0,
            "cover_image": "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1200&q=80", "الفخامة الهادئة لسيارة جينيسيس GV80 2024", 1, 1),
                ("image", "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80", "التصميم الجانبي الفخم مع الشبك الماسي ثنائي الخطوط", 2, 0)
            ]
        },
        {
            "slug": "audi-rs-q8-40-tfsi-2023",
            "brand": "Audi",
            "model": "RS Q8",
            "year": 2023,
            "trim": "Dynamic Package Plus",
            "country_of_origin": "Germany",
            "engine_capacity": "4.0L Twin-Turbo V8 (591 HP)",
            "fuel_type": "بنزين (Petrol)",
            "transmission": "أوتوماتيك 8-Speed Tiptronic Quattro",
            "mileage": 14000,
            "exterior_color": "رمادي دايتونا بيرل (Daytona Gray Pearl)",
            "interior_color": "جلد فالكونا أسود مع تطريزات ماسية حمراء RS",
            "vehicle_condition": "فابريكة بالكامل - وارد ألمانيا مع صيانة أودي الرسمية",
            "vin": "WAUZZZF16PD019284",
            "units_available": 1,
            "units_total": 1,
            "selling_price_egp": 11500000,
            "reservation_deposit_egp": 380000,
            "expected_delivery_time": "15 - 22 يوم عمل",
            "description_ar": "وحش الحلبات في شكل SUV فاخرة. أودي RS Q8 بمحرك لامبورجيني أوروس المشترك V8 توين تيربو بقوة 591 حصان. حزمة كربون فايبر كاملة، فرامل سيراميك عالية الأداء، نظام عادم رياضي RS بصوت زئيري مذهل، نظام صوتي Bang & Olufsen 3D Advanced، ونظام توجيه رباعي ديناميكي.",
            "description_en": "The ultimate performance luxury SUV. 2023 Audi RS Q8 with Dynamic Package Plus sharing its DNA and engine with the Lamborghini Urus. Powered by a 591 HP 4.0L Twin-Turbo V8 with RS Ceramic Brakes, RS Sport Exhaust, and Bang & Olufsen 3D Advanced Sound.",
            "technical_specs": json.dumps({
                "الأداء": {
                    "المحرك": "4.0 لتر V8 TFSI تيربو مزدوج مع نظام Mild-Hybrid 48V",
                    "القوة الحصانية": "591 حصان",
                    "عزم الدوران": "800 نيوتن.متر",
                    "التسارع 0-100 كم/س": "3.8 ثوانٍ",
                    "السرعة القصوى": "305 كم/س (مفتوحة مع Dynamic Package Plus)",
                    "نظام الدفع": "Quattro للدفع الرباعي المستمر مع ترس تفاضلي رياضي Sport Differential"
                },
                "التجهيزات الرياضية": {
                    "الفرامل": "فرامل سيراميك RS Ceramic Brakes مع ملاقط حمراء مقاس 440 مم",
                    "العادم": "عادم رياضي RS Sport Exhaust مع صمامات تحكم إلكترونية",
                    "الجنوط": "جنوط 23 بوصة بتصميم 5-Y-Spoke الماسي",
                    "الصوت": "نظام Bang & Olufsen Advanced 3D بـ 23 مكبر صوت وسماعات كهربائية صاعدة"
                }
            }, ensure_ascii=False),
            "additional_notes": "تقرير الفحص الفني الألماني TÜV SÜD ساري ومرفق مع السيارة.",
            "status": "available",
            "is_featured": 0,
            "is_latest": 1,
            "is_special_offer": 0,
            "cover_image": "https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?auto=format&fit=crop&w=1200&q=80",
            "media": [
                ("image", "https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?auto=format&fit=crop&w=1200&q=80", "التصميم الهجومي الخارق لـ أودي RS Q8", 1, 1),
                ("image", "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80", "الخطوط الخلفية الديناميكية ومخارج العادم البيضاوية RS", 2, 0)
            ]
        }
    ]

    for v in vehicles_list:
        media_items = v.pop("media")
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
            v["slug"], v["brand"], v["model"], v["year"], v["trim"], v["country_of_origin"],
            v["engine_capacity"], v["fuel_type"], v["transmission"], v["mileage"],
            v["exterior_color"], v["interior_color"], v["vehicle_condition"], v["vin"],
            v["units_available"], v["units_total"], v["selling_price_egp"], v["reservation_deposit_egp"],
            v["expected_delivery_time"], v["description_ar"], v["description_en"], v["technical_specs"],
            v["additional_notes"], v["status"], v["is_featured"], v["is_latest"], v["is_special_offer"],
            v["cover_image"], now, now
        ))
        vehicle_id = cursor.lastrowid

        for m in media_items:
            cursor.execute("""
                INSERT INTO vehicle_media (vehicle_id, media_type, url, caption, display_order, is_cover, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (vehicle_id, m[0], m[1], m[2], m[3], m[4], now))

    # Seed a sample active booking with real 9-stage tracking timeline
    cursor.execute("""
        INSERT INTO bookings (
            booking_code, vehicle_id, customer_name, customer_phone, customer_email,
            customer_city, customer_notes, status, deposit_paid, deposit_amount,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "SYR-2026-7842",
        1,  # Mercedes G63 AMG
        "المستشار حسام نور الدين",
        "+20 101 234 5678",
        "hossam.nour@gmail.com",
        "الإسكندرية - سابا باشا",
        "أرغب في استلام السيارة بميناء الإسكندرية فور إنهاء الإفراج الجمركي مباشرة.",
        "active_tracking",
        1,
        400000,
        "2026-10-18 11:30:00",
        now
    ))
    booking_id = cursor.lastrowid

    # Seed the 9 stages for tracking
    stages_data = [
        (
            1, "تأكيد الحجز والتعاقد الرسمي", "Reservation Confirmed & Agreement Signed",
            "completed", "2026-10-18 14:00", "مقر صالة عرض سيارتك - القاهرة الجديدة",
            "تم توقيع عقد الاستيراد واستلام إيداع جدية الحجز بنجاح وإصدار ملف الشحن الرسمي.",
            json.dumps(["https://images.unsplash.com/photo-1450133064473-71024230f91b?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            2, "شراء وفحص السيارة ببلد المنشأ", "Vehicle Purchased & Inspected in Germany",
            "completed", "2026-10-22 10:15", "صالة مرسيدس المعتمدة - شتوتغارت، ألمانيا",
            "تم شراء المركبة وإجراء الفحص الفني الدقيق الشامل (Dekra 111-Point Inspection) وتأكيد سلامة الفابريكة بنسبة 100%.",
            json.dumps(["https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=600&q=80", "https://images.unsplash.com/photo-1580273916550-e323be2ae537?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            3, "تجهيز السيارة للشحن الدولي والتوثيق", "Preparing for International Shipment",
            "completed", "2026-10-26 16:30", "ميناء هامبورغ - جمهورية ألمانيا الاتحادية",
            "تم استخراج شهادة اليورو 1 الموثقة، وإنهاء تصاريح التصدير وتثبيت المركبة في حاوية شحن بحري مخصصة (High Cube Container).",
            json.dumps(["https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            4, "انطلاق الشحنة البحرية من ألمانيا", "Shipped from Origin Country",
            "completed", "2026-10-28 08:00", "ميناء هامبورغ الدولي - المحيط الأطلسي",
            "إبحار السفينة الناقلة بوليصة شحن رقم BL#DE-EGY-991823 متجهة إلى البحر الأبيض المتوسط.",
            json.dumps(["https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            5, "الشحنة في طريقها البحري إلى مصر", "In Transit Across Mediterranean Sea",
            "completed", "2026-11-02 12:00", "البحر الأبيض المتوسط - قبالة السواحل المصرية",
            "السفينة تتبع المسار الملاحي المحدد بانتظام والظروف الجوية ممتازة وحالة الحاوية مستقرة.",
            json.dumps(["https://images.unsplash.com/photo-1559136555-9303baea8ebd?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            6, "وصول الشحنة لميناء الإسكندرية", "Arrived at Alexandria Seaport, Egypt",
            "completed", "2026-11-05 09:30", "ميناء الإسكندرية البحري - رصيف الحاويات",
            "تم تفريغ الحاوية بسلام في المنطقة الجمركية بميناء الإسكندرية وفحص سلامة الأختام الرسمية.",
            json.dumps(["https://images.unsplash.com/photo-1520031441872-265e4ff70366?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            7, "إجراءات التخليص الجمركي والفحص والتثمين", "Customs Clearance & Inspection in Egypt",
            "in_progress", "2026-11-07 01:00", "مجمع الجمارك - ميناء الإسكندرية",
            "جاري إنهاء إجراءات الفحص البيئي والمطابقة والتثمين الجمركي واستخراج إذن الإفراج النهائي.",
            json.dumps(["https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=600&q=80"])
        ),
        (
            8, "السيارة جاهزة للاستلام والترخيص", "Ready for Delivery & Licensing",
            "pending", None, "صالة عرض سيارتك - الإسكندرية / القاهرة",
            "يتم غسيل السيارة وتلميعها بالنانو سيراميك وتجهيز ملف الترخيص النهائي للتسليم.",
            json.dumps([])
        ),
        (
            9, "تم تسليم السيارة والمستندات للعميل", "Delivered Successfully to Customer",
            "pending", None, "موقع العميل أو صالة العرض",
            "تسليم المفتاحين الأصليين، كتيبات المصنع، وفاتورة الشراء والشهادة الجمركية.",
            json.dumps([])
        )
    ]

    for stage in stages_data:
        cursor.execute("""
            INSERT INTO tracking_stages (
                booking_id, stage_number, stage_title_ar, stage_title_en,
                status, completed_at, location, notes, proof_media
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (booking_id, stage[0], stage[1], stage[2], stage[3], stage[4], stage[5], stage[6], stage[7]))
