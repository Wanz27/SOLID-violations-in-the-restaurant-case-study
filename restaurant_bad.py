#  Program Manajemen Restoran — MELANGGAR prinsip SOLID
# ============================================================

import smtplib, json, sqlite3
from abc import ABC, abstractmethod

# ── [I] INTERFACE TERLALU GEMUK ──────────────────────────────

class StaffInterface(ABC):  # [I] Semua method digabung
    @abstractmethod
    def take_order(self): pass     # hanya untuk waiter
    @abstractmethod
    def cook_food(self): pass      # hanya untuk chef
    @abstractmethod
    def manage_staff(self): pass   # hanya untuk manager
    @abstractmethod
    def clean_table(self): pass    # hanya untuk cleaning


# ── [L] SUBCLASS MELANGGAR KONTRAK PARENT ────────────────────

class Waiter(StaffInterface):  # [L] Terpaksa implement semua
    def take_order(self): return "Waiter mencatat pesanan"
    def cook_food(self):
        raise NotImplementedError("Waiter tidak memasak!")
    def manage_staff(self):
        raise NotImplementedError("Waiter tidak manage staff!")
    def clean_table(self): return "Waiter bersihkan meja"

class Chef(StaffInterface):  # [L] Chef dipaksa punya take_order
    def take_order(self):
        raise NotImplementedError("Chef tidak ambil pesanan!")
    def cook_food(self): return "Chef memasak hidangan"
    def manage_staff(self):
        raise NotImplementedError("Chef tidak manage staff!")
    def clean_table(self):
        raise NotImplementedError("Chef tidak bersihkan meja!")


# ── [S] SATU CLASS TERLALU BANYAK TANGGUNG JAWAB ─────────────

class OrderManager:  # [S] Urus order + DB + email + laporan
    def __init__(self):
        self.db = sqlite3.connect("restoran.db")  # [D] Hardcode DB konkrit
        self.orders = []

    # Tanggung jawab 1: business logic pesanan
    def add_order(self, menu_item, qty, table_no):
        order = {"item": menu_item, "qty": qty, "table": table_no}
        self.orders.append(order)

        # Tanggung jawab 2: simpan ke database langsung
        self.db.execute(  # [S][D] DB logic di sini
            "INSERT INTO orders VALUES (?,?,?)",
            [menu_item, qty, table_no]
        )

        # Tanggung jawab 3: kirim notifikasi email
        smtp = smtplib.SMTP("smtp.gmail.com", 587)
        smtp.sendmail("restoran@gmail.com", "dapur@gmail.com",
                      f"Pesanan baru: {menu_item} x{qty} meja {table_no}")

        # Tanggung jawab 4: cetak laporan ke file
        with open("laporan.txt", "a") as f:
            f.write(f"Order: {menu_item} x{qty} meja {table_no}\n")

    def get_total(self):
        return len(self.orders)


# ── [O] HARUS EDIT KODE LAMA UNTUK TAMBAH FITUR ──────────────

class PaymentProcessor:  # [O] Tambah metode baru = ubah class ini
    def process(self, amount, method):
        if method == "cash":
            return f"Bayar tunai Rp{amount:,}"
        elif method == "card":
            return f"Bayar kartu Rp{amount:,}"
        elif method == "qris":
            return f"Bayar QRIS Rp{amount:,}"

        # Mau tambah GoPay/OVO/dana? HARUS edit method ini!
        elif method == "gopay":   # ditambah belakangan
            return f"Bayar GoPay Rp{amount:,}"
        elif method == "ovo":     # ditambah lagi
            return f"Bayar OVO Rp{amount:,}"
        else:
            return "Metode tidak dikenal"


# ── [D] HIGH-LEVEL BERGANTUNG KE IMPLEMENTASI KONKRIT ────────

class RestaurantApp:  # [D] Langsung pakai class konkrit
    def __init__(self):
        self.order_mgr  = OrderManager()      # [D] hardcode
        self.payment    = PaymentProcessor()   # [D] hardcode
        self.waiter     = Waiter()             # [D] hardcode

    def run(self, item, qty, table, amount, pay_method):
        print(self.waiter.take_order())
        self.order_mgr.add_order(item, qty, table)
        print(self.payment.process(amount, pay_method))


# ── PENGGUNAAN ────────────────────────────────────────────────

app = RestaurantApp()
app.run("Nasi Goreng", 2, 5, 50000, "qris")
