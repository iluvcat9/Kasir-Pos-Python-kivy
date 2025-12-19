from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView

from database import connect, now
from utilist import rupiah

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A6
from reportlab.lib.styles import getSampleStyleSheet

import os
import platform
import subprocess

# =========================
# PATH OUTPUT DEFAULT
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


# =========================
# FUNGS BANTU
# =========================
def open_pdf(path):
    """Buka PDF dengan viewer default sesuai OS"""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
    except Exception as e:
        print("Gagal membuka PDF:", e)


# =========================
# KELAS KASIR
# =========================
class KasirScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cart = {}   # {product_id: qty}
        self.total = 0
        self.build_ui()

    def on_pre_enter(self, *args):
        self.load_produk()

    # =========================
    # UI
    # =========================
    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=10, spacing=10)

        root.add_widget(
            Label(text="KASIR", font_size=22, size_hint_y=None, height=45)
        )

        # List Produk
        self.grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))

        scroll = ScrollView(size_hint_y=0.6)
        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        # Total
        self.lbl_total = Label(
            text="Total: Rp 0",
            font_size=18,
            size_hint_y=None,
            height=40
        )
        root.add_widget(self.lbl_total)

        # Bayar
        self.pay = TextInput(
            hint_text="Uang Bayar",
            input_filter="int",
            multiline=False
        )
        root.add_widget(self.pay)

        # Tombol Bayar
        btn_bayar = Button(
            text="BAYAR & STRUK",
            size_hint_y=None,
            height=50
        )
        btn_bayar.bind(on_press=self.bayar)
        root.add_widget(btn_bayar)

        # Logout
        btn_logout = Button(
            text="Logout",
            size_hint_y=None,
            height=45
        )
        btn_logout.bind(
            on_press=lambda x: setattr(self.manager, "current", "login")
        )
        root.add_widget(btn_logout)

        self.add_widget(root)

    # =========================
    # LOAD PRODUK
    # =========================
    def load_produk(self):
        self.grid.clear_widgets()
        conn = connect()
        c = conn.cursor()

        for pid, name, price, stock in c.execute(
            "SELECT id,name,price,stock FROM products WHERE stock > 0 ORDER BY name"
        ):
            btn = Button(
                text=f"{name} | Rp {rupiah(price)} | Stok {stock}",
                size_hint_y=None,
                height=45
            )
            btn.bind(
                on_press=lambda x, pid=pid, price=price: self.add(pid, price)
            )
            self.grid.add_widget(btn)

        conn.close()

    # =========================
    # TAMBAH KE KERANJANG
    # =========================
    def add(self, pid, price):
        self.cart[pid] = self.cart.get(pid, 0) + 1
        self.total += price
        self.lbl_total.text = f"Total: Rp {rupiah(self.total)}"

    # =========================
    # BAYAR
    # =========================
    def bayar(self, *args):
        if not self.pay.text:
            Popup(
                title="Error",
                content=Label(text="Masukkan uang bayar"),
                size_hint=(0.7, 0.3)
            ).open()
            return

        bayar = int(self.pay.text)
        if bayar < self.total:
            Popup(
                title="Error",
                content=Label(text="Uang kurang"),
                size_hint=(0.7, 0.3)
            ).open()
            return

        conn = connect()
        c = conn.cursor()

        # Simpan header transaksi
        c.execute(
            "INSERT INTO sales(total,bayar,kembalian,date) VALUES (?,?,?,?)",
            (self.total, bayar, bayar - self.total, now())
        )
        sale_id = c.lastrowid

        # Simpan detail & update stok
        for pid, qty in self.cart.items():
            c.execute(
                "SELECT name,price FROM products WHERE id=?",
                (pid,)
            )
            name, price = c.fetchone()

            c.execute(
                "INSERT INTO sales_items(sale_id,product_name,price,qty) VALUES (?,?,?,?)",
                (sale_id, name, price, qty)
            )

            c.execute(
                "UPDATE products SET stock = stock - ? WHERE id=?",
                (qty, pid)
            )

        conn.commit()
        conn.close()

        # Tampilkan struk
        self.popup_struk(sale_id)

        # Reset transaksi
        self.cart.clear()
        self.total = 0
        self.pay.text = ""
        self.lbl_total.text = "Total: Rp 0"
        self.load_produk()

    # =========================
    # POPUP STRUK
    # =========================
    def popup_struk(self, sale_id):
        box = BoxLayout(orientation="vertical", padding=10, spacing=5)
        box.add_widget(Label(text="STRUK TRANSAKSI", font_size=18))

        conn = connect()
        c = conn.cursor()

        c.execute(
            "SELECT total, bayar, kembalian, date FROM sales WHERE id=?",
            (sale_id,)
        )
        total, bayar, kembalian, date = c.fetchone()

        for name, price, qty in c.execute(
            "SELECT product_name,price,qty FROM sales_items WHERE sale_id=?",
            (sale_id,)
        ):
            box.add_widget(
                Label(text=f"{name} x{qty} = Rp {rupiah(price * qty)}")
            )

        conn.close()

        box.add_widget(Label(text=f"Total : Rp {rupiah(total)}"))
        box.add_widget(Label(text=f"Bayar : Rp {rupiah(bayar)}"))
        box.add_widget(Label(text=f"Kembali : Rp {rupiah(kembalian)}"))

        # Tombol CETAK PDF dengan pilih lokasi
        btn = Button(text="CETAK PDF", size_hint_y=None, height=40)
        btn.bind(on_press=lambda x: self.pilih_lokasi_pdf(sale_id))
        box.add_widget(btn)

        Popup(title="Struk", content=box, size_hint=(0.8, 0.8)).open()

    # =========================
    # PILIH LOKASI DAN NAMA FILE PDF
    # =========================
    def pilih_lokasi_pdf(self, sale_id):
        box = BoxLayout(orientation="vertical", spacing=5, padding=5)

        # FileChooser untuk pilih folder
        fc = FileChooserIconView(path=OUTPUT_DIR, dirselect=True)
        box.add_widget(fc)

        # TextInput untuk nama file
        nama_file_input = TextInput(text=f"struk_{sale_id}.pdf", multiline=False, size_hint_y=None, height=30)
        box.add_widget(Label(text="Nama file:"))
        box.add_widget(nama_file_input)

        # Tombol simpan
        btn_save = Button(text="Simpan PDF", size_hint_y=None, height=40)

        def save_pdf(instance):
            folder = fc.path
            nama_file = nama_file_input.text.strip()
            if not nama_file.endswith(".pdf"):
                nama_file += ".pdf"
            full_path = os.path.join(folder, nama_file)
            self.cetak_pdf(sale_id, full_path)
            popup.dismiss()

        btn_save.bind(on_press=save_pdf)
        box.add_widget(btn_save)

        popup = Popup(title="Pilih Lokasi & Nama File PDF", content=box, size_hint=(0.9, 0.9))
        popup.open()

    # =========================
    # CETAK PDF + BUKA OTOMATIS
    # =========================
    def cetak_pdf(self, sale_id, output_path=None):
        if not output_path:
            output_path = os.path.join(OUTPUT_DIR, f"struk_{sale_id}.pdf")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(output_path, pagesize=A6)
        styles = getSampleStyleSheet()
        content = []

        conn = connect()
        c = conn.cursor()

        c.execute(
            "SELECT total, bayar, kembalian, date FROM sales WHERE id=?",
            (sale_id,)
        )
        total, bayar, kembalian, date = c.fetchone()

        content.append(Paragraph("STRUK TRANSAKSI", styles["Title"]))
        content.append(Paragraph(date, styles["Normal"]))
        content.append(Paragraph("--------------------", styles["Normal"]))

        for name, price, qty in c.execute(
            "SELECT product_name,price,qty FROM sales_items WHERE sale_id=?",
            (sale_id,)
        ):
            content.append(
                Paragraph(f"{name} x{qty} = Rp {rupiah(price * qty)}", styles["Normal"])
            )

        conn.close()

        content.append(Paragraph("--------------------", styles["Normal"]))
        content.append(Paragraph(f"Total   : Rp {rupiah(total)}", styles["Normal"]))
        content.append(Paragraph(f"Bayar   : Rp {rupiah(bayar)}", styles["Normal"]))
        content.append(Paragraph(f"Kembali : Rp {rupiah(kembalian)}", styles["Normal"]))

        # Buat PDF
        doc.build(content)

        # Buka PDF otomatis
        open_pdf(output_path)

        # Popup sukses
        Popup(
            title="Sukses",
            content=Label(text=f"Struk PDF berhasil dibuat\n\n{output_path}"),
            size_hint=(0.75, 0.35)
        ).open()