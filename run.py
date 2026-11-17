import os
import sys
import uvicorn

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 60)
    print(" SYARTK - Exclusive Luxury Automotive Marketplace & Import Platform")
    print(f" Running at: http://{host}:{port}")
    print(f" Admin Portal: http://{host}:{port}/admin/login")
    print(" Default Admin Credentials: admin / motora2026admin")
    print("=" * 60)
    is_prod = bool(os.environ.get("PORT"))
    uvicorn.run("app.main:app", host=host, port=port, reload=not is_prod)
