import flet as ft
import json
import os
from datetime import datetime
from openpyxl import Workbook, load_workbook
import pandas as pd

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
        if os.path.exists(self.menu_file):
            try:
                with open(self.menu_file, 'r', encoding='utf-8') as f:
                    self.menu = json.load(f)
            except Exception as e:
                print(f"Error cargando menú: {e}")
                self.menu = {}
        else:
            self.menu = {
                "Duo Marino": 15.0,
                "Causa de Pescado": 10.0,
                "Ceviche": 12.0,
                "Trio Marino": 20.0,
            }
            self.save_menu()

    def save_menu(self):
        try:
            with open(self.menu_file, 'w', encoding='utf-8') as f:
                json.dump(self.menu, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error guardando menú: {e}")

    def add_dish(self, name, price):
        # Update if exists, else add new
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
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or row[0] is None: continue
                
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
                        'subtotal': float(row_data[6]) if row_data[6] is not None else (int(row_data[4]) * float(row_data[5])),
                        'metodo_pago': str(row_data[7]) if row_data[7] else "Efectivo",
                        'entregado': str(row_data[8]) == 'Si',
                        'pagado': str(row_data[9]) == 'Si'
                    }
                    self.orders.append(order)
                except Exception:
                    pass
        except Exception as e:
            print(f"Error cargando historial: {e}")

    def save_orders(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Historial Pedidos"
        headers = ["ID", "Fecha", "Cliente", "Plato", "Cant.", "Precio Unit.", "Total", "Método Pago", "Entregado", "Pagado"]
        ws.append(headers)
        
        for o in self.orders:
            ws.append([
                o['id'], o['fecha'], o['cliente'], o['plato'], o['cantidad'], o['precio'],
                o['subtotal'], o.get('metodo_pago', 'Efectivo'),
                "Si" if o['entregado'] else "No", "Si" if o['pagado'] else "No"
            ])
        try:
            wb.save(self.filename)
        except PermissionError as e:
            return str(e)
        return None

    def add_order(self, cliente, plato, cantidad, metodo_pago):
        if plato not in self.menu: return None
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
        return self.save_orders()

    def delete_order(self, order_id):
        self.orders = [o for o in self.orders if o['id'] != order_id]
        return self.save_orders()

    def toggle_status(self, order_id, field):
        for order in self.orders:
            if order['id'] == order_id:
                order[field] = not order[field]
                return self.save_orders()
        return None

    def get_filtered_stats(self, start_date=None, end_date=None):
        if not self.orders:
            return None
            
        df = pd.DataFrame(self.orders)
        
        # Date Conversion
        try:
            df['fecha_dt'] = pd.to_datetime(df['fecha'])
        except Exception:
            return None

        # Filter by Date Range
        if start_date and end_date:
            mask = (df['fecha_dt'] >= pd.to_datetime(start_date)) & (df['fecha_dt'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
            df_filtered = df.loc[mask]
        else:
             # Default to today if no range
            today = datetime.now().strftime("%Y-%m-%d")
            df_filtered = df[df['fecha'].str.startswith(today)]

        if df_filtered.empty:
            return {
                "total_sales": 0,
                "ticket_average": 0,
                "top_3_dishes": [],
                "bottom_3_dishes": [],
                "top_3_clients": [],
                "avg_price_per_dish": 0,
                "payment_methods": {},
                "daily_sales_trend": {}
            }

        # KPIs
        total_sales = df_filtered['subtotal'].sum()
        ticket_average = df_filtered['subtotal'].mean()
        
        # Top/Bottom Dishes
        dish_counts = df_filtered['plato'].value_counts()
        total_items = dish_counts.sum()
        
        top_3_dishes = [{"name": name, "pct": (count/total_items)*100} for name, count in dish_counts.head(3).items()]
        bottom_3_dishes = [{"name": name, "pct": (count/total_items)*100} for name, count in dish_counts.tail(3).items()]

        # Top Clients
        client_counts = df_filtered['cliente'].value_counts()
        total_clients = client_counts.sum()
        top_3_clients = [{"name": name, "pct": (count/total_clients)*100} for name, count in client_counts.head(3).items()]

        # Avg Price per Dish (Total Sales / Total Qty)
        total_qty = df_filtered['cantidad'].sum()
        avg_price_per_dish = total_sales / total_qty if total_qty > 0 else 0

        # Payment Methods
        payment_methods = df_filtered['metodo_pago'].value_counts().to_dict()

        # Daily Sales Trend (for LineChart)
        # Group by Date (YYYY-MM-DD) and sum subtotal at that day
        daily_sales = df_filtered.groupby(df_filtered['fecha_dt'].dt.date)['subtotal'].sum().to_dict()
        
        # Sort by date
        daily_sales = dict(sorted(daily_sales.items()))

        return {
            "total_sales": total_sales,
            "ticket_average": ticket_average,
            "top_3_dishes": top_3_dishes,
            "bottom_3_dishes": bottom_3_dishes,
            "top_3_clients": top_3_clients,
            "avg_price_per_dish": avg_price_per_dish,
            "payment_methods": payment_methods,
            "daily_sales_trend": daily_sales
        }

# ================= VISTA / UI (FLET) =================

def main(page: ft.Page):
    page.title = "Cevichería YAFRANK"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window.min_width = 1000
    page.window.min_height = 700

    manager = OrderManager()
    
    # 1. SALES VIEW COMPONENT
    def create_sales_view():
        
        menu_items_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        
        qty_input = ft.TextField(value="1", label="Cantidad", width=80, text_align="center", keyboard_type="number")
        
        payment_group = ft.RadioGroup(content=ft.Row([
            ft.Radio(value="Efectivo", label="Efectivo"),
            ft.Radio(value="Yape", label="Yape"),
            ft.Radio(value="Plin", label="Plin"),
        ]))
        payment_group.value = "Efectivo"
        
        search_input = ft.TextField(
            label="Buscar Cliente/Plato", 
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: filter_orders(e.control.value),
            expand=True
        )
        
        client_input = ft.TextField(label="Nombre Cliente", expand=True)

        client_input = ft.TextField(label="Nombre Cliente", expand=True)

        # --- TABLA DE VENTAS CON HEADER FIJO (Sticky Header) ---
        col_widths = [50, 120, 150, 150, 60, 80, 80, 100, 120]
        headers_txt = ["ID", "Fecha", "Cliente", "Plato", "Cant.", "Total", "Pago", "Estado", "Acciones"]
        
        header_row = ft.Row(
            controls=[
                ft.Container(content=ft.Text(h, weight="bold"), width=w) 
                for h, w in zip(headers_txt, col_widths)
            ],
            spacing=10
        )
        
        orders_header = ft.Container(
            content=header_row,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=10,
            border_radius=ft.border_radius.only(top_left=10, top_right=10),
        )

        orders_list = ft.ListView(expand=True, spacing=0)


        def refresh_orders_table_logic(orders_to_show=None):
            # PURE LOGIC
            orders_list.controls.clear()
            
            data_source = orders_to_show if orders_to_show is not None else manager.orders
            sorted_orders = sorted(data_source, key=lambda x: x['id'], reverse=True)
            
            for o in sorted_orders[:50]: 
                status_paid = "Pagado" if o['pagado'] else "Pendiente"
                status_del = "Entregado" if o['entregado'] else "Pendiente"
                
                color_paid = ft.Colors.GREEN if o['pagado'] else ft.Colors.RED
                color_del = ft.Colors.GREEN if o['entregado'] else ft.Colors.ORANGE

                row_controls = [
                    ft.Text(str(o['id'])),
                    ft.Text(str(o['fecha'])[:16]),
                    ft.Text(o['cliente']),
                    ft.Text(o['plato']),
                    ft.Text(str(o['cantidad'])),
                    ft.Text(f"S/{o['subtotal']:.2f}"),
                    ft.Text(o['metodo_pago']),
                    ft.Row([
                        ft.Container(content=ft.Text("P", size=10, color=ft.Colors.WHITE), bgcolor=color_paid, padding=5, border_radius=5, tooltip=f"Pago: {status_paid}"),
                        ft.Container(content=ft.Text("E", size=10, color=ft.Colors.WHITE), bgcolor=color_del, padding=5, border_radius=5, tooltip=f"Entrega: {status_del}"),
                    ], spacing=2),
                     ft.Row([
                        ft.IconButton("attach_money", icon_color=ft.Colors.GREEN, icon_size=20, tooltip="Marcar Pagado", on_click=lambda e, id=o['id']: toggle_paid_click(e, id)), 
                        ft.IconButton("delivery_dining", icon_color=ft.Colors.BLUE, icon_size=20, tooltip="Marcar Entregado", on_click=lambda e, id=o['id']: toggle_delivered_click(e, id)), 
                        ft.IconButton("delete", icon_color=ft.Colors.RED, icon_size=20, tooltip="Eliminar", on_click=lambda e, id=o['id']: delete_order_click(e, id)),
                    ], spacing=0)
                ]

                cells = [ft.Container(content=c, width=w) for c, w in zip(row_controls, col_widths)]
                
                orders_list.controls.append(
                    ft.Container(
                        content=ft.Row(cells, spacing=10),
                        padding=ft.padding.symmetric(vertical=5, horizontal=10),
                        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_200))
                    )
                )

        def refresh_menu_logic():
             # PURE LOGIC: Modifies the Control's state but DOES NOT call .update()
            menu_items_container.controls.clear()
            for dish, price in manager.menu.items():
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(dish, weight="bold", size=16),
                            ft.Text(f"S/ {price:.2f}", color=ft.Colors.GREEN)
                        ], expand=True),
                        ft.IconButton(
                            icon="add_circle", 
                            icon_color=ft.Colors.BLUE, 
                            icon_size=30,
                            tooltip="Agregar Pedido",
                            on_click=lambda e, d=dish: add_order_click(e, d)
                        )
                    ], alignment="spaceBetween"),
                    padding=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=10,
                )
                menu_items_container.controls.append(card)

        # Interaction Handlers
        def add_order_click(e, plato_name):
            if not client_input.value:
                # Assuming page.snack_bar is handled by page.update()
                page.snack_bar = ft.SnackBar(ft.Text("Ingrese Nombre del Cliente"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()
                return

            try:
                qty = int(qty_input.value)
            except ValueError:
                qty = 1
                
            err = manager.add_order(client_input.value, plato_name, qty, payment_group.value)
            if err:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error guardando: {err}"), bgcolor=ft.Colors.RED)
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Pedido Agregado: {plato_name}"), bgcolor=ft.Colors.GREEN)
                
                # Logic update
                refresh_orders_table_logic()
                if hasattr(create_dashboard_view, 'update_logic'):
                    create_dashboard_view.update_logic()
            
            page.snack_bar.open = True
            page.update() # Explicitly update the page after logic

        def delete_order_click(e, oid):
            manager.delete_order(oid)
            refresh_orders_table_logic()
            page.update() # Update page

        def toggle_paid_click(e, oid):
            manager.toggle_status(oid, 'pagado')
            refresh_orders_table_logic()
            page.update() # Update page

        def toggle_delivered_click(e, oid):
            manager.toggle_status(oid, 'entregado')
            refresh_orders_table_logic()
            page.update() # Update page
        
        # Search Logic
        def filter_orders(query):
            if not query:
                refresh_orders_table_logic()
            else:
                q = query.lower()
                filtered = [o for o in manager.orders if q in o['cliente'].lower() or q in o['plato'].lower()]
                refresh_orders_table_logic(filtered)
            page.update()

        # --- INITIAL DATA POPULATION ---
        refresh_menu_logic() 
        refresh_orders_table_logic()
        
        # Expose methods for external access
        create_sales_view.refresh_table = refresh_orders_table_logic
        create_sales_view.refresh_menu = refresh_menu_logic

        view = ft.Row([
            # Left Column (Menu)
            ft.Container(
                content=ft.Column([
                    ft.Text("Carta", size=20, weight="bold"),
                    ft.Divider(),
                    ft.Row([client_input]),
                    ft.Row([
                        qty_input,
                        payment_group
                    ], alignment="spaceBetween", vertical_alignment="center"),
                    ft.Divider(),
                    menu_items_container
                ]),
                width=350,
                padding=10,
                bgcolor=ft.Colors.SURFACE,
                border_radius=12,
            ),
            # Right Column (Orders)
            ft.Container(
                content=ft.Column([
                   ft.Row([
                       ft.Text("Pedidos Recientes", size=20, weight="bold"),
                       ft.IconButton("refresh", on_click=lambda e: (filter_orders(search_input.value), page.update()))
                   ], alignment="spaceBetween"),
                   ft.Row([search_input]), # Add Search Bar Row
                   ft.Row(
                       [
                           ft.Column([
                                orders_header,
                                orders_list
                           ], 
                           expand=True, 
                           spacing=0,
                           width=sum(col_widths) + 120 # Width sum + padding
                           )
                       ], 
                       scroll=ft.ScrollMode.AUTO, 
                       expand=True
                   ) 
                ]),
                expand=True,
                padding=10,
                border_radius=12,
                bgcolor=ft.Colors.SURFACE,
            )
        ], expand=True, spacing=10)
        
        return view

    # 2. DASHBOARD VIEW
    def create_dashboard_view():
        # Date Pickers
        start_date_picker = ft.DatePicker(
            on_change=lambda e: update_dashboard_logic(),
            first_date=datetime(2023, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        end_date_picker = ft.DatePicker(
             on_change=lambda e: update_dashboard_logic(),
            first_date=datetime(2023, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        page.overlay.append(start_date_picker)
        page.overlay.append(end_date_picker)

        btn_start_date = ft.ElevatedButton(
            "Desde", 
            icon=ft.Icons.CALENDAR_MONTH, 
            on_click=lambda _: start_date_picker.pick_date()
        )
        btn_end_date = ft.ElevatedButton(
            "Hasta", 
            icon=ft.Icons.CALENDAR_MONTH, 
            on_click=lambda _: end_date_picker.pick_date()
        )
        
        def clear_filters():
             start_date_picker.value = None
             end_date_picker.value = None
             update_dashboard_logic() 

        date_range_row = ft.Row([
            ft.Text("Filtrar por Fecha:", weight="bold"),
            btn_start_date,
            btn_end_date,
            ft.IconButton(icon=ft.Icons.FILTER_LIST_OFF, tooltip="Limpiar Filtros", on_click=lambda e: clear_filters())
        ], alignment="center", spacing=20)
        
        chart_payment = ft.PieChart(
            sections=[],
            sections_space=0,
            center_space_radius=40,
            expand=True
        )
        
        # Historical Chart (Line)
        chart_history = ft.LineChart(
            data_series=[],
            border=ft.border.all(3, ft.Colors.GREY),
            horizontal_grid_lines=ft.ChartGridLines(interval=100, color=ft.Colors.GREY, width=1),
            vertical_grid_lines=ft.ChartGridLines(interval=1, color=ft.Colors.GREY, width=1),
            left_axis=ft.ChartAxis(labels_size=40),
            bottom_axis=ft.ChartAxis(labels_interval=1),
            expand=True,
            tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
        )

        stat_total = ft.Text("S/ 0.00", size=30, weight="bold")
        stat_ticket = ft.Text("S/ 0.00", size=30, weight="bold")
        stat_avg_price = ft.Text("S/ 0.00", size=30, weight="bold")
        
        # Analysis containers
        top_dishes_col = ft.Column()
        bottom_dishes_col = ft.Column()
        top_clients_col = ft.Column()
        ai_insights_txt = ft.Text("", italic=True, size=14, color=ft.Colors.GREY_700)
        
        def update_dashboard_logic():
            # 1. Get Dates
            s_date = start_date_picker.value
            e_date = end_date_picker.value
            
            # Format UI buttons to show selected date
            btn_start_date.text = s_date.strftime("%Y-%m-%d") if s_date else "Desde"
            btn_end_date.text = e_date.strftime("%Y-%m-%d") if e_date else "Hasta"

            # 2. Prepare Data
            stats = manager.get_filtered_stats(s_date, e_date)
            
            if not stats: 
                # Zero state
                stat_total.value = "S/ 0.00"
                stat_ticket.value = "S/ 0.00"
                stat_avg_price.value = "S/ 0.00"
                chart_payment.sections = []
                chart_history.data_series = []
                top_dishes_col.controls = []
                bottom_dishes_col.controls = []
                top_clients_col.controls = []
                ai_insights_txt.value = "No hay datos para el rango de fechas seleccionado."
                page.update()
                return

            # 3. Update UI
            # KPIs
            stat_total.value = f"S/ {stats['total_sales']:.2f}"
            stat_ticket.value = f"S/ {stats['ticket_average']:.2f}"
            stat_avg_price.value = f"S/ {stats['avg_price_per_dish']:.2f}"
            
            # Pie Chart
            payment_sections = []
            colors = [ft.Colors.BLUE, ft.Colors.ORANGE, ft.Colors.GREEN, ft.Colors.PURPLE]
            total_orders_count = sum(stats['payment_methods'].values())
            
            for i, (method, count) in enumerate(stats['payment_methods'].items()):
                pct = (count / total_orders_count) * 100 if total_orders_count > 0 else 0
                payment_sections.append(
                    ft.PieChartSection(
                        value=count,
                        title=f"{pct:.0f}%",
                        color=colors[i % len(colors)],
                        radius=50,
                        title_style=ft.TextStyle(size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    )
                )
            chart_payment.sections = payment_sections
            
            # Historical Chart
            trend_points = []
            if stats['daily_sales_trend']:
                # We need numeric X for LineChart. We can use index 0,1,2... or timestamp.
                # Simplified: Use index and show date on tooltip or just index.
                # For better UX in Flet LineChart without complex date axis custom renderer,
                # we just plot values.
                dates = list(stats['daily_sales_trend'].keys())
                amounts = list(stats['daily_sales_trend'].values())
                
                for i, amt in enumerate(amounts):
                    trend_points.append(
                        ft.LineChartDataPoint(i, amt, tooltip=f"{dates[i]}: S/{amt:.2f}")
                    )
                
                chart_history.data_series = [
                    ft.LineChartData(
                        data_points=trend_points,
                        stroke_width=3,
                        color=ft.Colors.CYAN,
                        curved=True,
                        stroke_cap_round=True,
                        below_line_bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.CYAN),
                    )
                ]
                chart_history.min_y = 0
                chart_history.max_y = max(amounts) * 1.1 if amounts else 100
                chart_history.min_x = 0
                chart_history.max_x = len(amounts) - 1 if amounts else 0
            else:
                 chart_history.data_series = []

            # Lists (Top/Bottom)
            def build_mini_list(data, color):
                items = []
                for item in data:
                    items.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(item['name'], size=12, expand=True),
                                ft.Text(f"{item['pct']:.1f}%", size=12, weight="bold", color=color)
                            ]),
                            padding=5,
                            border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.Colors.GREY_300))
                        )
                    )
                return items

            top_dishes_col.controls = build_mini_list(stats['top_3_dishes'], ft.Colors.GREEN)
            bottom_dishes_col.controls = build_mini_list(stats['bottom_3_dishes'], ft.Colors.RED)
            top_clients_col.controls = build_mini_list(stats['top_3_clients'], ft.Colors.BLUE)

            # AI Insights Simulations
            trend_txt = "estable"
            if stats['total_sales'] > 500: trend_txt = "en crecimiento 🚀"
            elif stats['total_sales'] < 100: trend_txt = "baja 📉"
                
            ai_msg = f"Resumen: Tus ventas están {trend_txt}. El precio promedio de los platos es {stat_avg_price.value}. Se recomienda promocionar los platos menos vendidos."
            ai_insights_txt.value = ai_msg

            page.update()

        def stat_card(title, value_control, icon, color):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon, color=color), ft.Text(title, color=ft.Colors.GREY, size=12)]),
                    value_control
                ]),
                padding=15,
                bgcolor=ft.Colors.SURFACE, 
                border_radius=12,
                expand=True,
            )

        def info_card(title, content_col):
             return ft.Container(
                content=ft.Column([
                    ft.Text(title, weight="bold", size=14),
                    ft.Divider(height=10, thickness=1),
                    content_col
                ]),
                padding=15,
                bgcolor=ft.Colors.SURFACE, 
                border_radius=12,
                expand=True,
            )

        # Assemble View
        view = ft.Column([
            ft.Text("Dashboard de Negocio", size=24, weight="bold"),
            date_range_row,
            ft.Container(content=ai_insights_txt, bgcolor=ft.Colors.BLUE_50, padding=10, border_radius=8),
            
            # Row 1: KPIs
            ft.Row([
                stat_card("Venta Total", stat_total, ft.Icons.ATTACH_MONEY, ft.Colors.GREEN),
                stat_card("Ticket Promedio", stat_ticket, ft.Icons.RECEIPT, ft.Colors.BLUE),  
                stat_card("Precio Prom./Plato", stat_avg_price, ft.Icons.RESTAURANT_MENU, ft.Colors.ORANGE),  
            ]),
            
            # Row 2: Charts
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Métodos de Pago", weight="bold"),
                        chart_payment,
                        ft.Row([
                            ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.BLUE), ft.Text("Eft")]),
                            ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.ORANGE), ft.Text("Yape")]),
                            ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.GREEN), ft.Text("Plin")]),
                        ], alignment="center")
                    ], horizontal_alignment="center"),
                    expand=1,
                    bgcolor=ft.Colors.SURFACE,
                    padding=20,
                    border_radius=12,
                    height=300
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Evolución de Ventas (Diaria)", weight="bold"),
                        chart_history
                    ], horizontal_alignment="center"),
                    expand=2,
                    bgcolor=ft.Colors.SURFACE,
                    padding=20,
                    border_radius=12,
                    height=300
                )
            ], expand=True),

            # Row 3: Detailed Lists
            ft.Row([
                info_card("Top Platos Más Vendidos", top_dishes_col),
                info_card("Top Platos Menos Vendidos", bottom_dishes_col),
                info_card("Top Mejores Clientes", top_clients_col),
            ], expand=True)

        ], expand=True, scroll=ft.ScrollMode.AUTO)
        
        # Expose update method
        create_dashboard_view.update_logic = update_dashboard_logic
        
        # Populate initial state
        # Delay initial load slightly to ensure UI is ready or just call it:
        # update_dashboard_logic() -> Logic might fail if page overlay not ready? 
        # Safe to call but DatePickers start None.
        
        return view

    # 3. MANAGEMENT VIEW
    def create_management_view():
        name_input = ft.TextField(label="Nombre del Plato", expand=True)
        price_input = ft.TextField(label="Precio", width=100, keyboard_type="number")
        
        menu_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Plato")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            expand=True
        )

        def edit_dish_click(e, dish):
            price = manager.menu.get(dish, 0.0)
            name_input.value = dish
            price_input.value = str(price)
            # Focus on name
            name_input.focus()
            page.update()

        def refresh_mgmt_logic():
            # PURE LOGIC
            menu_table.rows.clear()
            for dish, price in manager.menu.items():
                menu_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(dish)),
                            ft.DataCell(ft.Text(f"S/ {price:.2f}")),
                            ft.DataCell(
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        icon_color=ft.Colors.AMBER,
                                        on_click=lambda e, d=dish: edit_dish_click(e, d),
                                        tooltip="Editar"
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE, 
                                        icon_color=ft.Colors.RED, 
                                        on_click=lambda e, d=dish: delete_dish_click(e, d),
                                        tooltip="Eliminar"
                                    )
                                ])
                            )
                        ]
                    )
                )

        def save_dish_click(e):
            if not name_input.value or not price_input.value:
                return
            try:
                p = float(price_input.value)
                manager.add_dish(name_input.value, p)
                name_input.value = ""
                price_input.value = ""
                
                # Logic
                refresh_mgmt_logic()
                if hasattr(create_sales_view, 'refresh_menu'):
                    create_sales_view.refresh_menu()
                
                page.update() # Update page
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("Precio inválido"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()

        def delete_dish_click(e, dish):
            manager.delete_dish(dish)
            refresh_mgmt_logic()
            if hasattr(create_sales_view, 'refresh_menu'):
                create_sales_view.refresh_menu()
            page.update()

        # Initial populate
        refresh_mgmt_logic()

        # Expose refresh method
        create_management_view.refresh_logic = refresh_mgmt_logic

        return ft.Container(
            content=ft.Column([
                ft.Text("Gestión de Carta", size=24, weight="bold"),
                ft.Container(
                    content=ft.Row([
                        name_input,
                        price_input,
                        ft.ElevatedButton("Guardar", on_click=save_dish_click, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE)
                    ]),
                    padding=20,
                    bgcolor=ft.Colors.SURFACE,
                    border_radius=12
                ),
                ft.Container(
                    content=menu_table,
                    padding=10,
                    bgcolor=ft.Colors.SURFACE,
                    border_radius=12,
                    expand=True
                )
            ]),
            padding=20,
            expand=True
        )

    # --- MAIN LAYOUT ASSEMBLY ---
    
    # Initialize views exactly ONCE
    sales_view = create_sales_view()
    dashboard_view = create_dashboard_view()
    management_view = create_management_view()
    
    content_area = ft.Container(content=sales_view, expand=True, padding=10)

    def nav_change(e):
        selected_index = e.control.selected_index
        
        # 1. Assign Content
        if selected_index == 0:
            content_area.content = sales_view
            create_sales_view.refresh_table() # Call logic
        elif selected_index == 1:
            content_area.content = dashboard_view
            create_dashboard_view.update_logic() # Call logic
        elif selected_index == 2:
            content_area.content = management_view
            create_management_view.refresh_logic() # Call logic
            
        # 2. Render Page (Single Update)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=400,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon="point_of_sale", 
                selected_icon="point_of_sale_outlined",
                label="Ventas"
            ),
            ft.NavigationRailDestination(
                icon="dashboard",
                selected_icon="dashboard_customize", 
                label="Dashboard"
            ),
            ft.NavigationRailDestination(
                icon="settings", 
                selected_icon_content=ft.Icon("settings"), 
                label="Gestión"
            ),
        ],
        on_change=nav_change,
        expand=True,
    )

    def theme_toggle(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        theme_icon.icon = "dark_mode" if page.theme_mode == ft.ThemeMode.LIGHT else "light_mode"
        page.update()

    theme_icon = ft.IconButton("dark_mode", on_click=theme_toggle)

    page.add(
        ft.Row(
            [
                ft.Column([
                    rail,
                    ft.Container(content=theme_icon, padding=10, alignment=ft.alignment.center)
                ], width=100),
                content_area,
            ],
            expand=True,
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
