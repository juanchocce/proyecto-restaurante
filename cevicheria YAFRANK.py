
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from openpyxl import Workbook, load_workbook
from datetime import datetime
import os
import json

# ================= MODELO / LÓGICA =================

class OrderManager:
    def __init__(self, filename="pedidos_cevicheria.xlsx", menu_file="menu.json"):
        self.filename = filename
        self.menu_file = menu_file
        self.orders = []
        self.menu = {}
        
        self.load_menu()
        self.load_orders()

    def load_menu(self):
        # Cargar menú desde JSON o crear por defecto
        if os.path.exists(self.menu_file):
            try:
                with open(self.menu_file, 'r', encoding='utf-8') as f:
                    self.menu = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Error cargando menú: {e}")
                self.menu = {}
        else:
            # Menú por defecto
            self.menu = {
                "Duo Marino": 15.0,
                "Causa de Pescado": 10.0,
                "Causa de Langostinos": 15.0,
                "Causa acevichada": 18.0,
                "Ceviche": 12.0,
                "Ceviche Mixto": 15.0,
                "Trio Marino": 20.0,
                "Chicharon de Pescado": 15.0,
                "Sudado de Pescado": 18.0,
            }
            self.save_menu()

    def save_menu(self):
        try:
            with open(self.menu_file, 'w', encoding='utf-8') as f:
                json.dump(self.menu, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando menú: {e}")

    def add_dish(self, name, price):
        self.menu[name] = float(price)
        self.save_menu()

    def delete_dish(self, name):
        if name in self.menu:
            del self.menu[name]
            self.save_menu()

    def get_next_id(self):
        if not self.orders:
            return 1
        return max(o['id'] for o in self.orders) + 1

    def load_orders(self):
        if not os.path.exists(self.filename):
            return

        try:
            wb = load_workbook(self.filename)
            ws = wb.active
            
            # Estructura esperada (10 cols): 
            # ID | Fecha | Cliente | Plato | Cant. | Precio | Total | Metodo | Entregado | Pagado
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                # Validar que la fila tenga datos suficientes
                if not row or row[0] is None: continue
                
                # Manejo de migración: si el Excel anterior tenía menos columnas, ajustar
                # El formato anterior tenía 8 columnas.
                # Si len(row) < 10, completamos con defaults
                
                row_data = list(row)
                while len(row_data) < 10:
                    row_data.append(None)

                try:
                    order = {
                        'id': int(row_data[0]),
                        'fecha': row_data[1],
                        'cliente': row_data[2],
                        'plato': row_data[3],
                        'cantidad': int(row_data[4]),
                        'precio': float(row_data[5]),
                        # Recalcular subtotal si no existe, o leer columna 6
                        'subtotal': float(row_data[6]) if row_data[6] is not None else (int(row_data[4]) * float(row_data[5])),
                        'metodo_pago': str(row_data[7]) if row_data[7] else "Efectivo",
                        'entregado': str(row_data[8]) == 'Si',
                        'pagado': str(row_data[9]) == 'Si'
                    }
                    self.orders.append(order)
                except Exception as e:
                    print(f"Fila ignorada/error: {row} -> {e}")
                    
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el historial: {e}")

    def save_orders(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Historial Pedidos"
        
        headers = ["ID", "Fecha", "Cliente", "Plato", "Cant.", "Precio Unit.", "Total", "Método Pago", "Entregado", "Pagado"]
        ws.append(headers)
        
        for o in self.orders:
            ws.append([
                o['id'],
                o['fecha'],
                o['cliente'],
                o['plato'],
                o['cantidad'],
                o['precio'],
                o['subtotal'],
                o.get('metodo_pago', 'Efectivo'),
                "Si" if o['entregado'] else "No",
                "Si" if o['pagado'] else "No"
            ])
            
        try:
            wb.save(self.filename)
        except PermissionError:
            messagebox.showerror("Error", "No se pudo guardar el pedido. Cierre el Excel si está abierto.")

    def add_order(self, cliente, plato, cantidad, metodo_pago):
        if plato not in self.menu:
            raise ValueError("Plato no existente")
        
        precio = self.menu[plato]
        
        order = {
            'id': self.get_next_id(),
            'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'cliente': cliente,
            'plato': plato,
            'cantidad': cantidad,
            'precio': precio,
            'subtotal': precio * cantidad,
            'metodo_pago': metodo_pago,
            'entregado': False,
            'pagado': False
        }
        self.orders.append(order)
        self.save_orders()
        return order

    def delete_order(self, order_id):
        self.orders = [o for o in self.orders if o['id'] != order_id]
        self.save_orders()

    def toggle_status(self, order_id, field):
        for order in self.orders:
            if order['id'] == order_id:
                if field in ['entregado', 'pagado']:
                    order[field] = not order[field]
                    self.save_orders()
                    return order
        return None

    def get_daily_total(self):
        today = datetime.now().strftime("%Y-%m-%d")
        total = 0.0
        count = 0
        for o in self.orders:
            if str(o['fecha']).startswith(today):
                total += o['subtotal']
                count += 1
        return count, total

    def export_daily_report_excel(self, filename="reporte_ventas_diarias.xlsx"):
        # Agrupar por fecha
        daily_sales = {} # "YYYY-MM-DD": {'total': 0.0, 'count': 0}
        
        for o in self.orders:
            # Extraer solo fecha YYYY-MM-DD
            fecha_solo = str(o['fecha']).split(" ")[0]
            if fecha_solo not in daily_sales:
                daily_sales[fecha_solo] = {'total': 0.0, 'count': 0}
            
            daily_sales[fecha_solo]['total'] += o['subtotal']
            daily_sales[fecha_solo]['count'] += 1
            
        # Crear Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Ventas Diarias"
        ws.append(["Fecha", "Nro Pedidos", "Venta Total (S/)"])
        
        # Ordenar por fecha descendente
        sorted_dates = sorted(daily_sales.keys(), reverse=True)
        
        for d in sorted_dates:
            data = daily_sales[d]
            ws.append([d, data['count'], data['total']])
            
        try:
            wb.save(filename)
            return True, f"Reporte generado: {filename}"
        except Exception as e:
            return False, f"Error generando reporte: {e}"

# ================= VISTA / UI =================

class MenuEditor(tk.Toplevel):
    def __init__(self, parent, manager, callback_refresh):
        super().__init__(parent)
        self.manager = manager
        self.callback_refresh = callback_refresh
        self.title("Editor de Menú")
        self.geometry("500x400")
        
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        # Frame Entradas
        form_frame = tk.Frame(self, pady=10)
        form_frame.pack(fill="x")
        
        tk.Label(form_frame, text="Nombre del Plato:").grid(row=0, column=0, padx=5)
        self.entry_name = tk.Entry(form_frame, width=20)
        self.entry_name.grid(row=0, column=1, padx=5)
        
        tk.Label(form_frame, text="Precio (S/):").grid(row=0, column=2, padx=5)
        self.entry_price = tk.Entry(form_frame, width=8)
        self.entry_price.grid(row=0, column=3, padx=5)
        
        btn_save = tk.Button(form_frame, text="Guardar / Actualizar", bg="#4CAF50", fg="white",
                             command=self.save_dish)
        btn_save.grid(row=0, column=4, padx=10)
        
        # Lista
        self.tree = ttk.Treeview(self, columns=("Plato", "Precio"), show="headings")
        self.tree.heading("Plato", text="Nombre del Plato")
        self.tree.heading("Precio", text="Precio")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Botón Eliminar
        btn_del = tk.Button(self, text="Eliminar Plato Seleccionado", bg="#E57373", fg="white",
                            command=self.delete_dish)
        btn_del.pack(pady=10)

    def refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for plato, precio in self.manager.menu.items():
            self.tree.insert("", "end", values=(plato, f"{precio:.2f}"))

    def save_dish(self):
        name = self.entry_name.get().strip()
        price_str = self.entry_price.get().strip()
        
        if not name or not price_str:
            messagebox.showwarning("Error", "Ingrese nombre y precio")
            return
        
        try:
            price = float(price_str)
        except ValueError:
            messagebox.showwarning("Error", "El precio debe ser un número")
            return
            
        self.manager.add_dish(name, price)
        self.entry_name.delete(0, tk.END)
        self.entry_price.delete(0, tk.END)
        self.refresh_list()
        self.callback_refresh() # Actualizar ventana principal

    def delete_dish(self):
        sel = self.tree.selection()
        if not sel: return
        
        plato = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Confirmar", f"¿Eliminar '{plato}' del menú?"):
            self.manager.delete_dish(plato)
            self.refresh_list()
            self.callback_refresh()

class CevicheriaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.manager = OrderManager()
        
        self.title("Sistema de Pedidos - Cevichería YAFRANK")
        self.geometry("1150x700")
        self.minsize(1000, 600)
        
        self.columnconfigure(0, weight=3) # Menú
        self.columnconfigure(1, weight=7) # Tabla
        self.rowconfigure(0, weight=1)

        self.create_widgets()
        self.refresh_all()

    def create_widgets(self):
        self.create_left_panel()
        self.create_right_panel()

    def create_left_panel(self):
        left_frame = tk.Frame(self, bg="#f0f0f0", padx=10, pady=10)
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        # Header Menú
        header_menu = tk.Frame(left_frame, bg="#f0f0f0")
        header_menu.pack(fill="x", pady=(0, 10))
        
        lbl_title = tk.Label(header_menu, text="CARTA", font=("Arial", 14, "bold"), bg="#f0f0f0")
        lbl_title.pack(side="left")
        
        btn_edit_menu = tk.Button(header_menu, text="⚙ Editar", command=self.open_menu_editor, font=("Arial", 9))
        btn_edit_menu.pack(side="right")

        # Lista de Platos
        self.dish_listbox = tk.Listbox(left_frame, font=("Arial", 11), selectmode=tk.SINGLE, height=15)
        self.dish_listbox.pack(fill="both", expand=True, pady=5)
        
        # Controles Agregar
        control_frame = tk.Frame(left_frame, bg="#f0f0f0")
        control_frame.pack(fill="x", pady=10)
        
        # Cantidad
        tk.Label(control_frame, text="Cant:", font=("Arial", 10), bg="#f0f0f0").grid(row=0, column=0, sticky="w")
        self.var_qty = tk.IntVar(value=1)
        tk.Spinbox(control_frame, from_=1, to=100, textvariable=self.var_qty, width=4, font=("Arial", 11))\
            .grid(row=0, column=1, padx=5)
            
        # Método de Pago
        tk.Label(control_frame, text="Pago:", font=("Arial", 10), bg="#f0f0f0").grid(row=0, column=2, sticky="w")
        self.combo_payment = ttk.Combobox(control_frame, values=["Efectivo", "Yape", "Plin"], width=8, state="readonly")
        self.combo_payment.current(0)
        self.combo_payment.grid(row=0, column=3, padx=5)
        
        # Botón Agregar
        btn_add = tk.Button(left_frame, text="AGREGAR AL PEDIDO", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                           command=self.add_order_ui)
        btn_add.pack(fill="x", pady=5)

        # Reportes
        report_frame = tk.LabelFrame(left_frame, text="Reportes", bg="#f0f0f0", padx=5, pady=5)
        report_frame.pack(fill="x", pady=20)
        
        tk.Button(report_frame, text="Resumen del Día (Total)", command=self.show_daily_report_popup).pack(fill="x", pady=2)
        tk.Button(report_frame, text="Generar Excel Ventas Diarias", command=self.generate_daily_excel, bg="#2196F3", fg="white").pack(fill="x", pady=2)

    def create_right_panel(self):
        right_frame = tk.Frame(self, bg="#ffffff", padx=10, pady=10)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        header_frame = tk.Frame(right_frame, bg="white")
        header_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(header_frame, text="Cliente:", font=("Arial", 11, "bold"), bg="white").pack(side="left")
        self.entry_client = tk.Entry(header_frame, font=("Arial", 11))
        self.entry_client.pack(side="left", padx=5, fill="x", expand=True)
        
        # Tabla
        columns = ("ID", "Fecha", "Cliente", "Plato", "Cant.", "Pago", "Total", "Entregado", "Pagado")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings")
        
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=30, stretch=False)
        self.tree.heading("Fecha", text="Fecha"); self.tree.column("Fecha", width=120, stretch=False)
        self.tree.heading("Cliente", text="Cliente"); self.tree.column("Cliente", width=100)
        self.tree.heading("Plato", text="Plato"); self.tree.column("Plato", width=150)
        self.tree.heading("Cant.", text="Cnt"); self.tree.column("Cant.", width=40, anchor="center")
        self.tree.heading("Pago", text="Pago"); self.tree.column("Pago", width=60, anchor="center")
        self.tree.heading("Total", text="Total"); self.tree.column("Total", width=70, anchor="e")
        self.tree.heading("Entregado", text="Entreg."); self.tree.column("Entregado", width=60, anchor="center")
        self.tree.heading("Pagado", text="Pagado"); self.tree.column("Pagado", width=60, anchor="center")
        
        self.tree.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Botones Acción
        action_frame = tk.Frame(right_frame, bg="white")
        action_frame.pack(fill="x", pady=10)
        
        tk.Button(action_frame, text="ELIMINAR SELECCIÓN", bg="#E57373", fg="white", command=self.delete_item).pack(side="left", padx=2)
        tk.Button(action_frame, text="LIMPIAR FORMULARIO", bg="#FF9800", fg="white", command=self.clean_form).pack(side="left", padx=2)
        
        tk.Button(action_frame, text="MARCAR PAGADO", bg="#2196F3", fg="white", command=lambda: self.toggle_selection("pagado")).pack(side="right", padx=2)
        tk.Button(action_frame, text="MARCAR ENTREGADO", bg="#8BC34A", fg="white", command=lambda: self.toggle_selection("entregado")).pack(side="right", padx=2)

    # ================= LOGICA UI =================

    def refresh_all(self):
        # Refresh Menu List
        self.dish_listbox.delete(0, tk.END)
        for plato, precio in self.manager.menu.items():
            self.dish_listbox.insert(tk.END, f"{plato} - S/ {precio:.2f}")
            
        # Refresh Orders Tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        sorted_orders = sorted(self.manager.orders, key=lambda x: x['id'], reverse=True)
        for order in sorted_orders:
            self.tree.insert("", "end", values=(
                order['id'],
                order['fecha'],
                order['cliente'],
                order['plato'],
                order['cantidad'],
                order.get('metodo_pago', 'Efectivo'),
                f"S/ {order['subtotal']:.2f}",
                "✔" if order['entregado'] else "No",
                "✔" if order['pagado'] else "No"
            ))

    def add_order_ui(self):
        cliente = self.entry_client.get().strip()
        if not cliente:
            messagebox.showwarning("Aviso", "Ingrese nombre del cliente")
            return

        selection = self.dish_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Seleccione un plato")
            return
            
        item_text = self.dish_listbox.get(selection[0])
        plato_nombre = item_text.split(" - S/")[0]
        cantidad = self.var_qty.get()
        metodo = self.combo_payment.get()

        self.manager.add_order(cliente, plato_nombre, cantidad, metodo)
        self.refresh_all()
        self.var_qty.set(1)

    def delete_item(self):
        selected = self.tree.selection()
        if not selected: return
        if not messagebox.askyesno("Confirmar", "Eliminar pedido del historial?"): return
        
        for item in selected:
            order_id = self.tree.item(item, "values")[0]
            self.manager.delete_order(int(order_id))
        self.refresh_all()

    def toggle_selection(self, field):
        for item in self.tree.selection():
            order_id = self.tree.item(item, "values")[0]
            self.manager.toggle_status(int(order_id), field)
        self.refresh_all()

    def clean_form(self):
        self.entry_client.delete(0, tk.END)

    def open_menu_editor(self):
        MenuEditor(self, self.manager, self.refresh_all)

    def show_daily_report_popup(self):
        count, total = self.manager.get_daily_total()
        date_str = datetime.now().strftime("%d/%m/%Y")
        msg = f"RESUMEN {date_str}\n\nPedidos: {count}\nVenta Total: S/ {total:.2f}"
        messagebox.showinfo("Reporte Diario", msg)

    def generate_daily_excel(self):
        ok, msg = self.manager.export_daily_report_excel()
        if ok: messagebox.showinfo("Éxito", msg)
        else: messagebox.showerror("Error", msg)

if __name__ == "__main__":
    app = CevicheriaApp()
    app.mainloop()
