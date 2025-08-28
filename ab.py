import os
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

DB = os.path.join(os.path.expanduser("~"), "Documents", "Invoice Generator", "invoices.db")
OUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Invoice Generator", "invoices")
os.makedirs(OUT_DIR, exist_ok=True)
def money(d):
    return Decimal(d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def ensure_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inv_no TEXT,
        date TEXT,
        customer_name TEXT,
        customer_address TEXT,
        subtotal TEXT,
        tax_total TEXT,
        total TEXT,
        logo_path TEXT,
        sign_path TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        description TEXT,
        qty TEXT,
        rate TEXT,
        gst_percent TEXT,
        discount_percent TEXT,
        amount TEXT
    )""")
    conn.commit()
    conn.close()
def next_invoice_no():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0] or 0
    conn.close()
    return f"INV-{count+1:04d}"
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

def generate_pdf(invoice_data, items, out_path):
    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4
    margin = 40
    header_bottom_y = height - margin
    logo_display_height = 0
    if invoice_data.get('logo_path'):
        try:
            img = ImageReader(invoice_data['logo_path'])
            img_width, img_height = img.getSize()
            aspect = img_height / float(img_width)
            display_width = 100
            display_height = display_width * aspect
            c.drawImage(img, margin, height - margin - display_height,
                        width=display_width, height=display_height, mask='auto')
            logo_display_height = display_height
            header_bottom_y = height - margin - display_height
        except Exception as e:
            print(f"Warning: Unable to load logo image: {e}")
    company_top_y = height - margin
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - margin, company_top_y, "My Company Pvt Ltd")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin, company_top_y - 14, "123 Business Road")
    c.drawRightString(width - margin, company_top_y - 26, "City, State ZIP")
    c.drawRightString(width - margin, company_top_y - 38, "Phone: +91 99999 99999")
    c.drawRightString(width - margin, company_top_y - 50, "GSTIN: 1234ABCDE")
    company_text_bottom = company_top_y - 50
    header_bottom_y = min(header_bottom_y, company_text_bottom) - 20  
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(margin, header_bottom_y, width - margin, header_bottom_y)
    title_y = header_bottom_y - 25
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, title_y, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(margin, title_y - 20, f"Invoice No: {invoice_data['inv_no']}")
    c.drawString(width / 2, title_y - 20, f"Date: {invoice_data['date']}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, title_y - 45, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(margin, title_y - 60, invoice_data.get('customer_name', ''))
    for i, line in enumerate(invoice_data.get('customer_address', '').splitlines()):
        c.drawString(margin, title_y - 72 - (i * 12), line)
    tbl_y = title_y - 110
    c.setFillColor(colors.darkgrey)
    c.rect(margin, tbl_y - 4, width - 2 * margin, 18, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 2, tbl_y, "Description")
    c.drawRightString(margin + 270, tbl_y, "Qty")
    c.drawRightString(margin + 340, tbl_y, "Price")
    c.drawRightString(width - margin, tbl_y, "Amount")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    cur_y = tbl_y - 16
    for it in items:
        c.drawString(margin, cur_y, it['description'])
        c.drawRightString(margin + 270, cur_y, str(it['qty']))
        c.drawRightString(margin + 340, cur_y, f"{money(it['rate'])}")
        c.drawRightString(width - margin, cur_y, f"{money(it['amount'])}")
        cur_y -= 16
        if cur_y < 150:
            c.showPage()
            cur_y = height - margin - 60
    total_y = cur_y - 10
    c.setStrokeColor(colors.grey)
    c.line(margin, total_y + 14, width - margin, total_y + 14)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - margin, total_y, f"Subtotal: {invoice_data['subtotal']}")
    c.drawRightString(width - margin, total_y - 14, f"Tax Total: {invoice_data['tax_total']}")
    c.drawRightString(width - margin, total_y - 28, f"Total: {invoice_data['total']}")
    sig_x = width - margin - 120
    sig_y = 100
    if invoice_data.get('sign_path'):
        try:
            c.drawImage(invoice_data['sign_path'], sig_x, sig_y,
                        width=100, preserveAspectRatio=True, mask='auto')
        except:
            print("Warning: Unable to load signature image.")
    c.setStrokeColor(colors.grey)
    c.line(margin, 80, width - margin, 80)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, 65, "Thanks For Shopping!")
    c.save()
class InvoiceApp:
    def __init__(self, root):
        self.root = root
        root.title("Invoice Generator")
        self.logo_path = None
        self.sign_path = None
        hdr = ttk.Frame(root, padding=8)
        hdr.pack(fill='x')
        ttk.Label(hdr, text="Customer Name").grid(row=0, column=0, sticky='w')
        self.cname = ttk.Entry(hdr, width=30); self.cname.grid(row=0, column=1, padx=6)
        ttk.Label(hdr, text="Date").grid(row=0, column=2, sticky='w')
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        ttk.Entry(hdr, textvariable=self.date_var, width=22).grid(row=0, column=3, padx=6)
        ttk.Button(hdr, text="Choose Logo", command=self.choose_logo).grid(row=1, column=0)
        ttk.Button(hdr, text="Choose Signature", command=self.choose_sign).grid(row=1, column=1)
        ttk.Label(hdr, text="Customer Address").grid(row=2, column=0, sticky='nw')
        self.caddress = tk.Text(hdr, width=60, height=3); self.caddress.grid(row=2, column=1, columnspan=5, padx=6, pady=6)
        itemsf = ttk.LabelFrame(root, text="Items", padding=8)
        itemsf.pack(fill='x', padx=8, pady=6)
        ttk.Label(itemsf, text="Description").grid(row=0, column=0)
        self.desc = ttk.Entry(itemsf, width=30); self.desc.grid(row=0, column=1, padx=4)
        ttk.Label(itemsf, text="Qty").grid(row=0, column=2)
        self.qty = ttk.Entry(itemsf, width=6); self.qty.grid(row=0, column=3)
        ttk.Label(itemsf, text="Price").grid(row=0, column=4)
        self.rate = ttk.Entry(itemsf, width=8); self.rate.grid(row=0, column=5)
        ttk.Label(itemsf, text="GST%").grid(row=0, column=6)
        self.gst = ttk.Entry(itemsf, width=5); self.gst.grid(row=0, column=7)
        self.gst.insert(0, "18")
        ttk.Label(itemsf, text="Disc%").grid(row=0, column=8)
        self.disc = ttk.Entry(itemsf, width=5); self.disc.grid(row=0, column=9)
        self.disc.insert(0, "0")
        ttk.Button(itemsf, text="Add Item", command=self.add_item).grid(row=0, column=10, padx=8)
        cols = ('description','qty','rate','gst_percent','discount_percent','amount')
        self.tree = ttk.Treeview(root, columns=cols, show='headings', height=8)
        for c in cols:
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=100)
        self.tree.pack(fill='both', padx=8, pady=6)
        bottom = ttk.Frame(root, padding=8)
        bottom.pack(fill='x')
        ttk.Button(bottom, text="Generate PDF & Save", command=self.generate_and_save).pack(side='left')
        ttk.Button(bottom, text="View Saved Invoices", command=self.view_invoices).pack(side='left', padx=6)
        ensure_db()
        os.makedirs(OUT_DIR, exist_ok=True)
    def choose_logo(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if p:
            self.logo_path = p
    def choose_sign(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if p:
            self.sign_path = p
    def add_item(self):
        try:
            desc = self.desc.get().strip()
            qty = Decimal(self.qty.get().strip())
            rate = Decimal(self.rate.get().strip())
            gstp = Decimal(self.gst.get().strip())
            discp = Decimal(self.disc.get().strip())
        except:
            messagebox.showerror("Error", "Invalid numeric values.")
            return
        line_total = qty * rate
        discount_amt = line_total * (discp / 100)
        taxable_amt = line_total - discount_amt
        gst_amt = taxable_amt * (gstp / 100)
        total_amt = money(taxable_amt + gst_amt)
        self.tree.insert('', 'end', values=(desc, str(qty), str(rate), str(gstp), str(discp), str(total_amt)))
        self.desc.delete(0,'end'); self.qty.delete(0,'end'); self.rate.delete(0,'end')

    def collect_items(self):
        rows = []
        for iid in self.tree.get_children():
            vals = self.tree.item(iid)['values']
            rows.append({
                'description': vals[0],
                'qty': Decimal(vals[1]),
                'rate': Decimal(vals[2]),
                'gst_percent': Decimal(vals[3]),
                'discount_percent': Decimal(vals[4]),
                'amount': Decimal(vals[5])
            })
        return rows
    def generate_and_save(self):
        cname = self.cname.get().strip()
        caddr = self.caddress.get("1.0", "end").strip()
        items = self.collect_items()
        if not items:
            messagebox.showerror("No items", "Add at least one item.")
            return
        subtotal = sum((it['qty'] * it['rate']) - ((it['qty'] * it['rate']) * (it['discount_percent'] / 100)) for it in items)
        tax_total = sum(((it['qty'] * it['rate']) - ((it['qty'] * it['rate']) * (it['discount_percent'] / 100))) * (it['gst_percent'] / 100) for it in items)
        total = subtotal + tax_total
        subtotal, tax_total, total = money(subtotal), money(tax_total), money(total)
        inv_no = next_invoice_no()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        invoice_data = {
            'inv_no': inv_no,
            'date': now,
            'customer_name': cname,
            'customer_address': caddr,
            'subtotal': str(subtotal),
            'tax_total': str(tax_total),
            'total': str(total),
            'logo_path': self.logo_path,
            'sign_path': self.sign_path
        }
        out_path = os.path.join(OUT_DIR, f"{inv_no}.pdf")
        generate_pdf(invoice_data, items, out_path)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO invoices (inv_no, date, customer_name, customer_address, subtotal, tax_total, total, logo_path, sign_path)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (inv_no, now, cname, caddr, str(subtotal), str(tax_total), str(total), self.logo_path, self.sign_path))
        inv_id = c.lastrowid
        for it in items:
            c.execute("INSERT INTO items (invoice_id, description, qty, rate, gst_percent, discount_percent, amount) VALUES (?,?,?,?,?,?,?)",
                      (inv_id, it['description'], str(it['qty']), str(it['rate']), str(it['gst_percent']), str(it['discount_percent']), str(it['amount'])))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", f"Invoice {inv_no} saved and PDF created:\n{out_path}")
    def view_invoices(self):
        top = tk.Toplevel(self.root)
        top.title("Saved Invoices")
        tree = ttk.Treeview(top, columns=('id','inv_no','date','customer','total'), show='headings')
        for h in ('id','inv_no','date','customer','total'):
            tree.heading(h, text=h.title())
        tree.pack(fill='both', expand=True)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id,inv_no,date,customer_name,total FROM invoices ORDER BY id DESC")
        for row in c.fetchall():
            tree.insert('', 'end', values=row)
        conn.close()
if __name__ == "__main__":
    root = tk.Tk()
    app = InvoiceApp(root)
    root.mainloop()
