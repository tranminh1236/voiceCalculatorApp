from sqlalchemy.orm import Session
from app.models import Province


PROVINCES: list[dict] = [
    # Miền Bắc
    {"code": "HN", "region": "mb", "name": "Hà Nội"},

    # Miền Trung
    {"code": "DNG", "region": "mt", "name": "Đà Nẵng"},
    {"code": "KH", "region": "mt", "name": "Khánh Hòa"},
    {"code": "TTH", "region": "mt", "name": "Thừa Thiên Huế"},
    {"code": "PY", "region": "mt", "name": "Phú Yên"},
    {"code": "DLK", "region": "mt", "name": "Đắk Lắk"},
    {"code": "QNM", "region": "mt", "name": "Quảng Nam"},
    {"code": "DNO", "region": "mt", "name": "Đắk Nông"},
    {"code": "NT", "region": "mt", "name": "Ninh Thuận"},
    {"code": "GL", "region": "mt", "name": "Gia Lai"},
    {"code": "QNG", "region": "mt", "name": "Quảng Ngãi"},
    {"code": "BD", "region": "mt", "name": "Bình Định"},
    {"code": "QT", "region": "mt", "name": "Quảng Trị"},
    {"code": "QB", "region": "mt", "name": "Quảng Bình"},
    {"code": "KT", "region": "mt", "name": "Kon Tum"},

    # Miền Nam
    {"code": "TPHCM", "region": "mn", "name": "TP. Hồ Chí Minh"},
    {"code": "DT", "region": "mn", "name": "Đồng Tháp"},
    {"code": "CM", "region": "mn", "name": "Cà Mau"},
    {"code": "BL", "region": "mn", "name": "Bạc Liêu"},
    {"code": "BTR", "region": "mn", "name": "Bến Tre"},
    {"code": "VT", "region": "mn", "name": "Vũng Tàu"},
    {"code": "BTH", "region": "mn", "name": "Bình Thuận"},
    {"code": "DN", "region": "mn", "name": "Đồng Nai"},
    {"code": "CT", "region": "mn", "name": "Cần Thơ"},
    {"code": "ST", "region": "mn", "name": "Sóc Trăng"},
    {"code": "TN", "region": "mn", "name": "Tây Ninh"},
    {"code": "AG", "region": "mn", "name": "An Giang"},
    {"code": "VL", "region": "mn", "name": "Vĩnh Long"},
    {"code": "BDU", "region": "mn", "name": "Bình Dương"},
    {"code": "TG", "region": "mn", "name": "Tiền Giang"},
    {"code": "KG", "region": "mn", "name": "Kiên Giang"},
    {"code": "LA", "region": "mn", "name": "Long An"},
    {"code": "HG", "region": "mn", "name": "Hậu Giang"},
    {"code": "BP", "region": "mn", "name": "Bình Phước"},
    {"code": "TV", "region": "mn", "name": "Trà Vinh"},
]


def seed_provinces(session: Session) -> int:
    """Insert provinces if not exist. Returns number inserted."""
    existing = {p.code for p in session.query(Province).all()}
    inserted = 0
    for entry in PROVINCES:
        if entry["code"] in existing:
            continue
        session.add(Province(**entry))
        inserted += 1
    return inserted
