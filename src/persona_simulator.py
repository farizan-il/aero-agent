import random
from typing import Dict, Any, List


class UserPersona:
    """Definisi persona pengguna manusia dengan pola perilaku dan input yang unik."""

    def __init__(self, name: str, code: str, description: str, traits: List[str]):
        self.name = name
        self.code = code
        self.description = description
        self.traits = traits

    def generate_input_value(self, field_type: str, field_name: str) -> str:
        """Menghasilkan nilai input spesifik berdasarkan karakter persona."""
        raise NotImplementedError


class NormalUserPersona(UserPersona):
    """Pengguna Ideal: Mengisi data dengan benar sesuai alur sistem."""

    def __init__(self):
        super().__init__(
            name="Pengguna Standar (Ideal/Happy Path)",
            code="NORMAL",
            description="Mengikuti petunjuk alur, mengisi form dengan format yang valid dan sopan.",
            traits=["Form input valid", "Menunggu loading selesai", "Single click"],
        )

    def generate_input_value(self, field_type: str, field_name: str) -> str:
        fn = field_name.lower()
        if "email" in fn or field_type == "email":
            return "user.testing@aero-qa.com"
        elif "pass" in fn or field_type == "password":
            return "AeroSecure123!#"
        elif "phone" in fn or "tel" in fn or "hp" in fn:
            return "081298765432"
        elif "name" in fn or "nama" in fn:
            return "Budi Pratama"
        elif "search" in fn or "cari" in fn or "q" in fn:
            return "layanan"
        elif "number" in fn or field_type == "number":
            return "10"
        return "Data Uji Normal"


class ImpatientUserPersona(UserPersona):
    """Pengguna Tidak Sabaran: Melakukan klik berkali-kali secara cepat, navigasi terburu-buru."""

    def __init__(self):
        super().__init__(
            name="Pengguna Terburu-buru (Impatient / Rage Clicker)",
            code="IMPATIENT",
            description="Melakukan klik tombol berulang kali dengan cepat (double/triple submit), tidak sabar menunggu respon API.",
            traits=["Rage clicking", "Double submission", "Spam tombol", "Cepat berpindah halaman"],
        )

    def generate_input_value(self, field_type: str, field_name: str) -> str:
        return NormalUserPersona().generate_input_value(field_type, field_name)


class CluelessUserPersona(UserPersona):
    """Pengguna Ceroboh / Bingung: Typo, format keliru, input kosong, emoji berlebih."""

    def __init__(self):
        super().__init__(
            name="Pengguna Ceroboh / Bingung (Clueless User)",
            code="CLUELESS",
            description="Memasukkan format data salah (email tanpa @, huruf di kolom angka), spasi kosong, dan typo acak.",
            traits=["Email tanpa domain", "Karakter spasi saja", "Input angka dimasuki huruf", "Emoji di nama"],
        )

    def generate_input_value(self, field_type: str, field_name: str) -> str:
        fn = field_name.lower()
        if "email" in fn or field_type == "email":
            return "budi.email_tanpa_domain"
        elif "phone" in fn or "tel" in fn or field_type == "number":
            return "nomor_telepon_bukan_angka"
        elif "pass" in fn or field_type == "password":
            return "123"  # Terlalu pendek
        elif "name" in fn:
            return "   "  # Whitespace only
        return "??? 🤔❓"


class AdversarialPersona(UserPersona):
    """Penguji Celah / Edge Case Explorer: Menguji input ekstrem, payload keamanan & batas memori."""

    def __init__(self):
        super().__init__(
            name="Penguji Ekstrem / Boundary Explorer",
            code="ADVERSARIAL",
            description="Mengirimkan input ribuan karakter, payload XSS/SQLi ringan, zero-width spaces, dan karakter simbol.",
            traits=["Boundary text (5000+ char)", "XSS probe sanitasi", "SQL probe escape", "Karakter Unicode ekstrem"],
        )

    def generate_input_value(self, field_type: str, field_name: str) -> str:
        fn = field_name.lower()
        options = [
            "<script>console.log('AERO_XSS_TEST')</script>",
            "' OR '1'='1' --",
            "A" * 1200,  # Buffer / Length boundary
            "SELECT * FROM users WHERE '1'='1';",
            "Null \x00 Byte & 特殊文字 🚀 🔥",
        ]
        return random.choice(options)


class MobilePersona(UserPersona):
    """Pengguna Perangkat Mobile: Menguji tampilan layar kecil, sentuhan, dan menu tersembunyi."""

    def __init__(self):
        super().__init__(
            name="Pengguna Mobile Smartphone (Viewport Responsive)",
            code="MOBILE",
            description="Mengakses via layar iPhone (393x852), menguji overflow horizontal, hamburger menu, dan tombol kecil.",
            traits=["Layar kecil (Mobile viewport)", "Uji horizontal scrolling", "Penyusutan elemen"],
        )

    def generate_input_value(self, field_type: str, field_name: str) -> str:
        return NormalUserPersona().generate_input_value(field_type, field_name)


# Daftar Persona Tersedia
ALL_PERSONAS = {
    "NORMAL": NormalUserPersona(),
    "IMPATIENT": ImpatientUserPersona(),
    "CLUELESS": CluelessUserPersona(),
    "ADVERSARIAL": AdversarialPersona(),
    "MOBILE": MobilePersona(),
}
