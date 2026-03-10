# 🍽️ Analisis Pelanggaran Prinsip SOLID
### Studi Kasus: Program Manajemen Restoran (Python)

---

## 📋 Deskripsi Program

File `restaurant_bad.py` adalah simulasi sistem manajemen restoran sederhana yang **sengaja dirancang** untuk mengandung semua lima pelanggaran prinsip SOLID secara bersamaan dalam satu file utuh.

Program ini memiliki class-class untuk:
- Manajemen staf → `Waiter`, `Chef`
- Pemrosesan pesanan → `OrderManager`
- Pembayaran → `PaymentProcessor`
- Aplikasi utama → `RestaurantApp`

---

## ⚠️ Ringkasan Pelanggaran

| # | Prinsip | Class yang Melanggar | Baris | Inti Masalah |
|---|---------|----------------------|-------|--------------|
| S | Single Responsibility | `OrderManager` | 41–67 | Satu class mengurus 4 tanggung jawab sekaligus |
| O | Open/Closed | `PaymentProcessor` | 71–85 | `if-elif` harus diedit setiap ada metode bayar baru |
| L | Liskov Substitution | `Waiter`, `Chef` | 22–37 | Subclass throw `NotImplementedError` untuk method tidak relevan |
| I | Interface Segregation | `StaffInterface` | 10–18 | Interface terlalu gemuk, paksa semua staf implement semua method |
| D | Dependency Inversion | `OrderManager`, `RestaurantApp` | 43, 89–93 | Hardcode `sqlite3` dan class konkrit di dalam constructor |

---

## 🔍 Analisis Detail Per Prinsip

---

### S — Single Responsibility Principle

> *Setiap class hanya boleh punya satu alasan untuk berubah.*

**📍 Lokasi:** `class OrderManager` — baris 41–67

**Kode bermasalah:**
```python
class OrderManager:                          # [S] Urus order + DB + email + laporan
    def __init__(self):
        self.db = sqlite3.connect("restoran.db")
        self.orders = []

    def add_order(self, menu_item, qty, table_no):
        order = {"item": menu_item, "qty": qty, "table": table_no}
        self.orders.append(order)            # Tanggung jawab 1: business logic

        self.db.execute(                     # Tanggung jawab 2: simpan ke database
            "INSERT INTO orders VALUES (?,?,?)",
            [menu_item, qty, table_no]
        )

        smtp = smtplib.SMTP("smtp.gmail.com", 587)   # Tanggung jawab 3: kirim email
        smtp.sendmail("restoran@gmail.com", "dapur@gmail.com",
                      f"Pesanan baru: {menu_item} x{qty} meja {table_no}")

        with open("laporan.txt", "a") as f:  # Tanggung jawab 4: cetak laporan
            f.write(f"Order: {menu_item} x{qty} meja {table_no}\n")
```

**❌ Letak Kesalahan:**
- Method `add_order()` melakukan **4 hal berbeda** sekaligus: tambah pesanan ke list, simpan ke SQLite, kirim email via SMTP, dan cetak laporan ke file `.txt`
- Jika format laporan berubah → class ini harus dibuka, padahal logika pesanan tidak berubah sama sekali
- Jika provider email diganti (Gmail → SendGrid) → kode logika pesanan ikut terdampak
- Sulit di-*unit test* karena semua lapisan saling tergantung dalam satu class

**✅ Solusi:**
```python
class OrderService:        # Hanya urus business logic pesanan
    def add_order(self, item, qty, table):
        return {"item": item, "qty": qty, "table": table}

class OrderRepository:     # Hanya urus penyimpanan ke database
    def __init__(self, db):
        self.db = db
    def save(self, order):
        self.db.execute("INSERT INTO orders VALUES (?,?,?)",
                        [order["item"], order["qty"], order["table"]])

class NotificationService: # Hanya urus pengiriman notifikasi
    def send(self, order):
        smtp = smtplib.SMTP("smtp.gmail.com", 587)
        smtp.sendmail("restoran@gmail.com", "dapur@gmail.com", str(order))

class ReportService:       # Hanya urus pencetakan laporan
    def write(self, order):
        with open("laporan.txt", "a") as f:
            f.write(f"Order: {order}\n")
```

---

### O — Open/Closed Principle

> *Terbuka untuk ekstensi, tertutup untuk modifikasi.*

**📍 Lokasi:** `class PaymentProcessor` — baris 71–85

**Kode bermasalah:**
```python
class PaymentProcessor:                      # [O] Tambah metode baru = ubah class ini
    def process(self, amount, method):
        if method == "cash":
            return f"Bayar tunai Rp{amount:,}"
        elif method == "card":
            return f"Bayar kartu Rp{amount:,}"
        elif method == "qris":
            return f"Bayar QRIS Rp{amount:,}"
        elif method == "gopay":              # ditambah belakangan → edit kode lama
            return f"Bayar GoPay Rp{amount:,}"
        elif method == "ovo":               # ditambah lagi → edit kode lama lagi
            return f"Bayar OVO Rp{amount:,}"
        else:
            return "Metode tidak dikenal"
```

**❌ Letak Kesalahan:**
- Setiap metode pembayaran baru (GoPay, OVO, Dana, ShopeePay) mengharuskan developer **membuka dan mengedit** method `process()` yang sudah ada
- Setiap modifikasi berisiko merusak logika pembayaran lain yang sudah berjalan (*regression bug*)
- Blok `if-elif` yang terus memanjang → sulit dibaca, sulit di-*review*, sulit dipelihara

**✅ Solusi:**
```python
from abc import ABC, abstractmethod

class PaymentMethod(ABC):           # Abstraksi — tidak pernah diubah
    @abstractmethod
    def pay(self, amount): pass

class CashPayment(PaymentMethod):   # Tambah metode baru = buat class baru
    def pay(self, amount):
        return f"Bayar tunai Rp{amount:,}"

class CardPayment(PaymentMethod):
    def pay(self, amount):
        return f"Bayar kartu Rp{amount:,}"

class GopayPayment(PaymentMethod):  # Cukup tambah class ini, kode lama tidak disentuh
    def pay(self, amount):
        return f"Bayar GoPay Rp{amount:,}"

class PaymentProcessor:             # Kode ini TIDAK perlu diubah sama sekali
    def process(self, payment: PaymentMethod, amount):
        return payment.pay(amount)
```

---

### L — Liskov Substitution Principle

> *Subclass harus bisa menggantikan parent class tanpa merusak perilaku program.*

**📍 Lokasi:** `class Waiter` & `class Chef` — baris 22–37

**Kode bermasalah:**
```python
class Waiter(StaffInterface):       # [L] Terpaksa implement semua method
    def take_order(self):
        return "Waiter mencatat pesanan"
    def cook_food(self):
        raise NotImplementedError("Waiter tidak memasak!")   # ❌ crash!
    def manage_staff(self):
        raise NotImplementedError("Waiter tidak manage staff!")  # ❌ crash!
    def clean_table(self):
        return "Waiter bersihkan meja"

class Chef(StaffInterface):         # [L] Chef dipaksa punya take_order
    def take_order(self):
        raise NotImplementedError("Chef tidak ambil pesanan!")   # ❌ crash!
    def cook_food(self):
        return "Chef memasak hidangan"
    def manage_staff(self):
        raise NotImplementedError("Chef tidak manage staff!")    # ❌ crash!
    def clean_table(self):
        raise NotImplementedError("Chef tidak bersihkan meja!")  # ❌ crash!
```

**❌ Letak Kesalahan:**
- `Waiter` dipaksa punya method `cook_food()` padahal waiter tidak memasak → di-*raise* exception
- `Chef` dipaksa punya `take_order()` dan `manage_staff()` yang juga di-*raise* exception
- Fungsi yang memanggil `staff.cook_food()` dengan argumen bertipe `StaffInterface` akan **crash** saat menerima objek `Waiter` — padahal secara tipe, `Waiter` adalah `StaffInterface`
- Programmer harus selalu cek tipe objek sebelum memanggil method → ini bukan *polymorphism* yang sehat

**✅ Solusi:**
```python
# Pecah interface (sekaligus menyelesaikan pelanggaran ISP)
class OrderTaker(ABC):
    @abstractmethod
    def take_order(self): pass

class FoodCook(ABC):
    @abstractmethod
    def cook_food(self): pass

class TableCleaner(ABC):
    @abstractmethod
    def clean_table(self): pass

class Waiter(OrderTaker, TableCleaner): # Hanya implement yang relevan
    def take_order(self):
        return "Waiter mencatat pesanan"
    def clean_table(self):
        return "Waiter bersihkan meja"

class Chef(FoodCook):                   # Chef hanya implement FoodCook
    def cook_food(self):
        return "Chef memasak hidangan"

# Dijamin aman — setiap subclass bisa substitusi parent-nya
def do_cook(cook: FoodCook):
    cook.cook_food()  # tidak akan pernah crash

do_cook(Chef())   # ✅ OK
```

---

### I — Interface Segregation Principle

> *Class tidak boleh dipaksa mengimplementasi method yang tidak dibutuhkan.*

**📍 Lokasi:** `class StaffInterface` — baris 10–18

**Kode bermasalah:**
```python
class StaffInterface(ABC):          # [I] Semua method digabung dalam satu interface
    @abstractmethod
    def take_order(self): pass      # hanya relevan untuk waiter
    @abstractmethod
    def cook_food(self): pass       # hanya relevan untuk chef
    @abstractmethod
    def manage_staff(self): pass    # hanya relevan untuk manager
    @abstractmethod
    def clean_table(self): pass     # hanya relevan untuk cleaning staff
```

**❌ Letak Kesalahan:**
- Tidak ada satu pun staf restoran yang melakukan keempat pekerjaan itu sekaligus
- Setiap class yang mengimplementasi interface ini terpaksa "*pura-pura bisa*" melakukan semua hal dengan melempar exception
- Jika method baru ditambahkan ke interface (misal `make_report()`), **semua** class yang implement harus ikut dimodifikasi meskipun tidak relevan
- Ini adalah *fat interface* yang menciptakan *coupling* tinggi antar komponen yang tidak berhubungan

**✅ Solusi:**
```python
# Pecah menjadi interface kecil sesuai peran
class OrderTaker(ABC):
    @abstractmethod
    def take_order(self): pass

class FoodCook(ABC):
    @abstractmethod
    def cook_food(self): pass

class StaffManager(ABC):
    @abstractmethod
    def manage_staff(self): pass

class TableCleaner(ABC):
    @abstractmethod
    def clean_table(self): pass

# Setiap class hanya implement interface yang relevan
class Waiter(OrderTaker, TableCleaner): ...   # tidak perlu cook/manage
class Chef(FoodCook): ...                     # hanya masak
class Manager(StaffManager, OrderTaker): ...  # sesuai kebutuhan
```

---

### D — Dependency Inversion Principle

> *High-level module harus bergantung pada abstraksi, bukan implementasi konkrit.*

**📍 Lokasi:** `class OrderManager` (baris 43) & `class RestaurantApp` (baris 89–93)

**Kode bermasalah:**
```python
class OrderManager:
    def __init__(self):
        self.db = sqlite3.connect("restoran.db")  # [D] Hardcode ke SQLite!
        self.orders = []

class RestaurantApp:                              # [D] Langsung pakai class konkrit
    def __init__(self):
        self.order_mgr = OrderManager()           # hardcode
        self.payment   = PaymentProcessor()       # hardcode
        self.waiter    = Waiter()                 # hardcode

    def run(self, item, qty, table, amount, pay_method):
        print(self.waiter.take_order())
        self.order_mgr.add_order(item, qty, table)
        print(self.payment.process(amount, pay_method))
```

**❌ Letak Kesalahan:**
- `OrderManager.__init__` langsung membuat `sqlite3.connect("restoran.db")` → **terkunci ke SQLite**, tidak bisa ganti database tanpa buka dan edit class ini
- `RestaurantApp` membuat sendiri semua instance dependency-nya → tidak bisa diganti atau di-*mock* saat *unit testing*
- Tidak mungkin menulis *unit test* yang terisolasi karena semua dependency ter-*hardcode* di dalam constructor
- Melanggar *Dependency Injection* — dependency seharusnya disuntikkan dari luar, bukan dibuat di dalam

**✅ Solusi:**
```python
from abc import ABC, abstractmethod

class DatabaseInterface(ABC):       # Abstraksi — high-level bergantung ke ini
    @abstractmethod
    def save(self, data): pass
    @abstractmethod
    def query(self, sql): pass

class SQLiteDatabase(DatabaseInterface):    # Implementasi konkrit
    def save(self, data): ...
    def query(self, sql): ...

class PostgreSQLDatabase(DatabaseInterface): # Ganti DB = buat class baru
    def save(self, data): ...
    def query(self, sql): ...

class OrderManager:
    def __init__(self, db: DatabaseInterface):  # Terima abstraksi, bukan konkrit
        self.db = db

class RestaurantApp:
    def __init__(self, order_mgr, payment, waiter): # Semua disuntikkan dari luar
        self.order_mgr = order_mgr
        self.payment   = payment
        self.waiter    = waiter

# Ganti database tanpa ubah class apapun
app = RestaurantApp(
    order_mgr = OrderManager(SQLiteDatabase()),  # atau PostgreSQLDatabase()
    payment   = PaymentProcessor(),
    waiter    = Waiter()
)
```

---

## 🔗 Keterkaitan Antar Pelanggaran

Beberapa pelanggaran dalam kode ini saling berkaitan dan memperkuat satu sama lain:

| Hubungan | Penjelasan |
|----------|------------|
| **I → L** | Interface yang terlalu gemuk (ISP) adalah **akar penyebab** subclass terpaksa throw `NotImplementedError` (LSP). Memperbaiki ISP otomatis menyelesaikan pelanggaran LSP juga. |
| **S ↔ D** | Class yang punya terlalu banyak tanggung jawab (SRP) hampir selalu juga hardcode dependency-nya (DIP). `OrderManager` melanggar keduanya: mengurus DB sendiri sekaligus membuat koneksi `sqlite3` secara langsung. |
| **O + D** | `PaymentProcessor` melanggar OCP karena tidak bisa diperluas tanpa modifikasi, dan `RestaurantApp` memperparahnya dengan hardcode instance tanpa abstraksi. |

---

## 📌 Quick Reference — Cara Mendeteksi Pelanggaran SOLID

| Prinsip | Gejala dalam Kode | Pertanyaan Kunci |
|---------|-------------------|------------------|
| **S** | Method panjang dengan banyak `import` berbeda dalam satu class | *"Berapa alasan class ini bisa berubah?"* |
| **O** | Blok `if-elif` / `switch` yang terus memanjang seiring fitur baru | *"Harus edit file lama untuk tambah fitur?"* |
| **L** | Override method dengan `raise NotImplementedError` atau `return None` | *"Apakah subclass aman dipakai di mana parent dipakai?"* |
| **I** | Interface dengan banyak method abstrak yang tidak semua relevan | *"Ada method yang terpaksa dikosongkan?"* |
| **D** | `new ClassName()` di dalam constructor, import library konkrit di class bisnis | *"Apakah class ini bisa di-test tanpa dependensi aslinya?"* |

---

> **Catatan:** Dokumen ini merupakan analisis studi kasus pelanggaran prinsip SOLID pada program manajemen restoran berbasis Python. Kode `restaurant_bad.py` sengaja dibuat buruk untuk tujuan pembelajaran.
