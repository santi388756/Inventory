import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from datetime import datetime

import customtkinter as ctk

import analytics
from config import (
    APP_NAME, COLOR_DANGER, COLOR_DANGER_HOVER, COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_WARNING, COLOR_WARNING_HOVER,
)
from db import Database, DatabaseError

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_view = "Panel"
        self.prod_id_actual = None
        self.cli_id_actual = None
        self._carrito = []
        self._mapa_productos = {}
        self._mapa_clientes = {}

        self.title(APP_NAME)
        self.geometry("1280x800")
        self.minsize(1080, 700)

        self._configurar_estilos()
        self._construir_shell()
        self._construir_panel()
        self._construir_venta_rapida()
        self._construir_productos()
        self._construir_clientes()
        self._construir_pedidos()
        self._construir_datos()
        self._construir_estadisticas()
        self._mostrar_vista("Panel")
        self._cargar_todo()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _campo(self, parent, placeholder):
        """Crea un campo de texto consistente para los formularios."""
        entry = ctk.CTkEntry(parent, height=38, placeholder_text=placeholder)
        entry.pack(fill="x", padx=18, pady=5)
        return entry

    def _notificacion(self, titulo, mensaje, tipo="info"):
        colores = {
            "success": (COLOR_SUCCESS, "✓", "#F0FDF4", "#052E16"),
            "warning": (COLOR_WARNING, "!", "#FFFBEB", "#451A03"),
            "error": (COLOR_DANGER, "×", "#FEF2F2", "#450A0A"),
            "info": (COLOR_PRIMARY, "i", "#EFF6FF", "#172554"),
        }
        acento, icono, claro, oscuro = colores.get(tipo, colores["info"])
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=claro)
        width, height = 380, 104
        self.update_idletasks()
        target_x = self.winfo_rootx() + self.winfo_width() - width - 24
        target_y = self.winfo_rooty() + 24 + len(getattr(self, "_toasts", [])) * (height + 10)
        start_x = target_x + 42
        toast.geometry(f"{width}x{height}+{start_x}+{target_y}")
        self._toasts = getattr(self, "_toasts", [])
        self._toasts.append(toast)

        outer = ctk.CTkFrame(toast, corner_radius=16, fg_color=(claro, "#111827"), border_width=1, border_color=("#E2E8F0", "#263244"))
        outer.pack(fill="both", expand=True)
        icon = ctk.CTkFrame(outer, width=42, height=42, corner_radius=12, fg_color=("#FFFFFF", "#172033"), border_width=1, border_color=(acento, acento))
        icon.pack(side="left", padx=(14, 10), pady=14)
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, text=icono, text_color=(acento, acento), font=ctk.CTkFont(size=18, weight="bold")).pack(expand=True)
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=12)
        ctk.CTkLabel(body, text=titulo, anchor="w", text_color=(oscuro, "#F8FAFC"), font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x")
        ctk.CTkLabel(body, text=mensaje, anchor="w", justify="left", wraplength=265, text_color=("#64748B", "#CBD5E1"), font=ctk.CTkFont(size=10)).pack(fill="x", pady=(3, 4))
        progress = ctk.CTkProgressBar(body, height=3, corner_radius=2, fg_color=("#E2E8F0", "#243044"), progress_color=acento)
        progress.pack(fill="x", pady=(1, 0))
        progress.set(1)

        duration = 3600
        steps = 30
        def animate(step=0):
            if not toast.winfo_exists():
                return
            x = int(start_x + (target_x - start_x) * min(step / steps, 1))
            toast.geometry(f"{width}x{height}+{x}+{target_y}")
            if step < steps:
                toast.after(12, lambda: animate(step + 1))
        animate()

        def countdown(left=duration):
            if not toast.winfo_exists():
                return
            progress.set(max(0, left / duration))
            if left <= 0:
                close()
            else:
                toast.after(50, lambda: countdown(left - 50))

        def close():
            if not toast.winfo_exists():
                return
            current_x = toast.winfo_x()
            def slide(step=0):
                if not toast.winfo_exists():
                    return
                x = int(current_x + (start_x - current_x) * min(step / steps, 1))
                toast.geometry(f"{width}x{height}+{x}+{target_y}")
                if step < steps:
                    toast.after(10, lambda: slide(step + 1))
                else:
                    if toast in self._toasts:
                        self._toasts.remove(toast)
                    toast.destroy()
            slide()
        toast.after(250, countdown)

    def _dialogo_confirmacion(self, titulo, mensaje):
        dialog = ctk.CTkToplevel(self)
        dialog.title(titulo)
        dialog.geometry("430x235")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        result = {"ok": False}
        ctk.CTkLabel(dialog, text=titulo, anchor="w", font=ctk.CTkFont(size=20, weight="bold")).pack(fill="x", padx=26, pady=(25, 8))
        ctk.CTkLabel(dialog, text=mensaje, anchor="w", justify="left", wraplength=375, text_color=("#475569", "#CBD5E1"), font=ctk.CTkFont(size=11)).pack(fill="x", padx=26, pady=(0, 20))
        actions=ctk.CTkFrame(dialog, fg_color="transparent")
        actions.pack(fill="x", padx=26, pady=(0, 24))
        ctk.CTkButton(actions, text="Cancelar", height=40, corner_radius=9, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=dialog.destroy).pack(side="left", expand=True, fill="x", padx=(0,5))
        def aceptar():
            result["ok"] = True
            dialog.destroy()
        ctk.CTkButton(actions, text="Confirmar", height=40, corner_radius=9, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=aceptar).pack(side="left", expand=True, fill="x", padx=(5,0))
        self.wait_window(dialog)
        return result["ok"]

    def _info(self, titulo, mensaje, parent=None):
        self._notificacion(titulo, mensaje, "info")

    def _success(self, titulo, mensaje):
        self._notificacion(titulo, mensaje, "success")

    def _warning(self, titulo, mensaje, parent=None):
        self._notificacion(titulo, mensaje, "warning")

    def _error(self, titulo, mensaje, parent=None):
        self._notificacion(titulo, mensaje, "error")

    def _configurar_estilos(self):
        self.option_add("*Font", ("Segoe UI", 10))
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Inventory.Treeview",
            rowheight=42,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Inventory.Treeview.Heading",
            font=("Segoe UI Semibold", 10),
            padding=(10, 10),
            relief="flat",
        )
        style.map("Inventory.Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", "#111827")])

    def _construir_shell(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#F8FAFC", "#111827"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="Inventory", anchor="w",
            font=ctk.CTkFont(size=25, weight="bold")
        ).pack(fill="x", padx=24, pady=(30, 3))
        ctk.CTkLabel(
            self.sidebar, text="Gestión simple, sin complicaciones", anchor="w",
            text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=11)
        ).pack(fill="x", padx=24, pady=(0, 28))

        self.nav_buttons = {}
        self._nav_section("VENTAS")
        for name in ("Venta rápida",):
            self.nav_buttons[name] = self._nav_button(name)
        self._nav_section("ENTIDADES")
        for name in ("Productos", "Clientes", "Pedidos"):
            self.nav_buttons[name] = self._nav_button(name)
        self._nav_section("ANÁLISIS")
        self.nav_buttons["Estadísticas"] = self._nav_button("Estadísticas")
        self._nav_section("DATOS")
        self.nav_buttons["Datos"] = self._nav_button("Datos")

        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        ctk.CTkLabel(
            self.sidebar, text="Todo en un solo lugar", anchor="w",
            text_color=("#94A3B8", "#64748B"), font=ctk.CTkFont(size=10)
        ).pack(fill="x", padx=24, pady=(0, 24))

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("#F1F5F9", "#0B1120"))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.topbar = ctk.CTkFrame(self.content, height=76, corner_radius=0, fg_color=("#FFFFFF", "#111827"))
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_columnconfigure(0, weight=1)

        self.page_title = ctk.CTkLabel(self.topbar, text="Panel", anchor="w", font=ctk.CTkFont(size=24, weight="bold"))
        self.page_title.grid(row=0, column=0, padx=28, pady=(16, 0), sticky="w")
        self.page_hint = ctk.CTkLabel(
            self.topbar, text="Vista general de tu negocio", anchor="w",
            text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=11)
        )
        self.page_hint.grid(row=1, column=0, padx=28, pady=(0, 14), sticky="w")

        self.appearance = ctk.CTkOptionMenu(
            self.topbar, values=["Sistema", "Claro", "Oscuro"], width=105,
            command=self._cambiar_apariencia, fg_color=("#E2E8F0", "#1E293B"),
            button_color=("#E2E8F0", "#1E293B"), button_hover_color=("#CBD5E1", "#334155"),
            text_color=("#334155", "#E2E8F0")
        )
        self.appearance.set("Sistema")
        self.appearance.grid(row=0, column=1, rowspan=2, padx=28)

        self.views = {}
        self._view_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self._view_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
        self._view_frame.grid_rowconfigure(0, weight=1)
        self._view_frame.grid_columnconfigure(0, weight=1)

    def _nav_section(self, title):
        ctk.CTkLabel(
            self.sidebar, text=title, anchor="w",
            text_color=("#94A3B8", "#64748B"),
            font=ctk.CTkFont(size=9, weight="bold")
        ).pack(fill="x", padx=24, pady=(9, 3))

    def _nav_button(self, name):
        icons = {"Panel":"⌂", "Venta rápida":"⚡", "Productos":"▤", "Clientes":"♙", "Pedidos":"🛒", "Estadísticas":"◒", "Datos":"⇅"}
        button = ctk.CTkButton(
            self.sidebar, text=f"{icons.get(name, '•')}   {name}", anchor="w", height=46, corner_radius=10,
            fg_color="transparent", hover_color=("#E2E8F0", "#1E293B"),
            text_color=("#334155", "#CBD5E1"), font=ctk.CTkFont(size=13),
            command=lambda n=name: self._mostrar_vista(n),
        )
        button.pack(fill="x", padx=14, pady=3)
        return button

    def _cambiar_apariencia(self, value):
        ctk.set_appearance_mode({"Sistema": "System", "Claro": "Light", "Oscuro": "Dark"}[value])
        # Los Canvas no reciben automáticamente el cambio de tema.
        self.after(80, self._redibujar_graficos_tema)

    def _redibujar_graficos_tema(self):
        if hasattr(self, "canvas_grafico"):
            self._dibujar_grafico()
        if hasattr(self, "canvas_stats"):
            self._dibujar_stats()

    def _mostrar_vista(self, nombre):
        for frame in self.views.values():
            frame.grid_forget()
        self.views[nombre].grid(row=0, column=0, sticky="nsew")
        self.current_view = nombre
        self.page_title.configure(text=nombre)
        hints = {
            "Panel": "Vista general de tu negocio",
            "Venta rápida": "Registrá un cobro en segundos",
            "Productos": "Agregá y actualizá tu inventario",
            "Clientes": "Mantené tus contactos organizados",
            "Pedidos": "Prepará una venta en pocos pasos",
            "Estadísticas": "Entendé cómo se mueve tu negocio",
            "Datos": "Importá o exportá tu información",
        }
        self.page_hint.configure(text=hints[nombre])
        for n, b in self.nav_buttons.items():
            if n == nombre:
                b.configure(fg_color=("#DBEAFE", "#1E3A5F"), text_color=("#1D4ED8", "#93C5FD"))
            else:
                b.configure(fg_color="transparent", text_color=("#334155", "#CBD5E1"))

    def _new_view(self, name):
        frame = ctk.CTkFrame(self._view_frame, fg_color="transparent")
        self.views[name] = frame
        return frame

    # --------------------------- Panel ---------------------------
    def _construir_panel(self):
        view = self._new_view("Panel")
        view.grid_columnconfigure(0, weight=1)
        view.grid_columnconfigure(1, weight=1)
        view.grid_columnconfigure(2, weight=1)
        view.grid_rowconfigure(3, weight=1)

        intro = ctk.CTkFrame(view, fg_color="transparent")
        intro.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(intro, text="¿Qué querés hacer?", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(intro, text="↻  Actualizar", width=115, height=34, corner_radius=9, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=self._actualizar_panel).pack(side="right")

        modes = ctk.CTkFrame(view, fg_color="transparent")
        modes.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        for i in range(2): modes.grid_columnconfigure(i, weight=1)
        self._mode_card(modes, 0, "⚡", "Venta rápida", "Cobrá en segundos con monto y descripción.", "Venta rápida")
        self._mode_card(modes, 1, "▤", "Entidades", "Administrá productos, clientes y pedidos.", "Productos")

        self.kpi_productos = self._kpi(view, 0, "Productos", "0", "Artículos registrados", row=2)
        self.kpi_alertas = self._kpi(view, 1, "Stock bajo", "0", "Necesitan atención", warning=True, row=2)
        self.kpi_ventas_semana = self._kpi(view, 2, "Ventas 7 días", "0", "Facturación registrada", row=2)

        left = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        left.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(0, 9))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="Inventario", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=18, pady=16, sticky="w")

        columns = ("nombre", "stock", "venta", "dias", "tendencia")
        self.tree_panel = ttk.Treeview(left, columns=columns, show="headings", style="Inventory.Treeview")
        labels = {"nombre": "Producto", "stock": "Stock", "venta": "Venta / semana", "dias": "Días restantes", "tendencia": "Tendencia"}
        widths = {"nombre": 230, "stock": 80, "venta": 120, "dias": 115, "tendencia": 105}
        for col in columns:
            self.tree_panel.heading(col, text=labels[col])
            self.tree_panel.column(col, width=widths[col], anchor="center")
        self.tree_panel.column("nombre", anchor="w")
        self.tree_panel.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.tree_panel.tag_configure("alerta", background="#FEF2F2")
        self.tree_panel.tag_configure("ok", background="#F0FDF4")

        right = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        right.grid(row=3, column=2, sticky="nsew", padx=(9, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="Ventas · últimos 14 días", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        ctk.CTkLabel(right, text="Incluye ventas rápidas y ventas del catálogo", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=9)).grid(row=0, column=0, padx=18, pady=(35, 10), sticky="w")

        self.canvas_grafico = tk.Canvas(
            right, highlightthickness=0, bd=0,
            bg="#FFFFFF"
        )
        self.canvas_grafico.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.canvas_grafico.bind("<Configure>", lambda _event: self._dibujar_grafico())
        self._datos_grafico = []
        self._datos_ventas_diarias = []

    def _mode_card(self, parent, column, icon, title, description, target):
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E2E8F0", "#1E293B"))
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 5, 5 if column < 2 else 0))
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=icon, width=42, height=42, corner_radius=12, fg_color=("#EFF6FF", "#172033"), text_color=(COLOR_PRIMARY, "#93C5FD"), font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=14)
        ctk.CTkLabel(card, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, sticky="ew", pady=(13, 1))
        ctk.CTkLabel(card, text=description, anchor="w", justify="left", wraplength=190, text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=9)).grid(row=1, column=1, sticky="ew", pady=(0, 13))
        ctk.CTkButton(card, text="Abrir →", width=78, height=30, corner_radius=8, fg_color="transparent", hover_color=("#DBEAFE", "#1E3A5F"), text_color=(COLOR_PRIMARY, "#93C5FD"), command=lambda: self._mostrar_vista(target)).grid(row=0, column=2, rowspan=2, padx=(6, 12))

    def _kpi(self, parent, column, title, value, caption, warning=False, row=1):
        frame = ctk.CTkFrame(parent, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 6, 6 if column < 2 else 0), pady=(0, 18))
        icon_map={"Productos":"▦","Stock bajo":"!","Ventas 7 días":"↗"}
        ctk.CTkLabel(frame, text=icon_map.get(title,"•"), width=28, height=28, corner_radius=8, fg_color=("#EFF6FF","#172033"), text_color=(COLOR_PRIMARY,"#93C5FD"), font=ctk.CTkFont(size=13,weight="bold")).pack(anchor="w", padx=18, pady=(13, 3))
        ctk.CTkLabel(frame, text=title, text_color=("#475569", "#94A3B8"), font=ctk.CTkFont(size=10)).pack(anchor="w", padx=18, pady=(0, 2))
        value_label = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=28, weight="bold"))
        value_label.pack(anchor="w", padx=18)
        ctk.CTkLabel(frame, text=caption, text_color=("#94A3B8", "#64748B"), font=ctk.CTkFont(size=10)).pack(anchor="w", padx=18, pady=(0, 15))
        if warning:
            ctk.CTkFrame(frame, width=4, height=36, corner_radius=2, fg_color=COLOR_WARNING).place(x=0, y=18)
        frame.valor_label = value_label
        return frame

    def _actualizar_panel(self):
        try:
            productos = self.db.get_productos()
            ventas_raw = self.db.get_ventas_historicas()
            df = analytics.metricas_por_producto(ventas_raw, productos)
        except DatabaseError as e:
            self._error("No se pudo actualizar", str(e))
            return

        self.kpi_productos.valor_label.configure(text=str(len(productos)))
        alertas = sum(1 for fila in df if fila["alerta"])
        self.kpi_alertas.valor_label.configure(text=str(alertas))
        try:
            diarios = self.db.get_ventas_diarias(7)
            total_7 = sum(float(x.get("total") or 0) for x in diarios)
            self._datos_ventas_diarias = diarios
            self.kpi_ventas_semana.valor_label.configure(text=self._fmt(total_7))
        except DatabaseError:
            self.kpi_ventas_semana.valor_label.configure(text="$ 0.00")

        for item in self.tree_panel.get_children():
            self.tree_panel.delete(item)
        for fila in df:
            dias = "—" if fila["dias_para_agotarse"] is None else fila["dias_para_agotarse"]
            tags = ("alerta",) if fila["alerta"] else ("ok",)
            tendencia = str(fila["tendencia"]).capitalize()
            self.tree_panel.insert("", "end", values=(fila["nombre"], fila["stock_actual"], fila["venta_semanal_estimada"], dias, tendencia), tags=tags)

        try:
            self._datos_ventas_diarias = self.db.get_ventas_diarias(14)
        except DatabaseError:
            self._datos_ventas_diarias = []
        self._datos_grafico = analytics.top_productos_por_venta(df, 5)
        self._dibujar_grafico()

    def _dibujar_grafico(self):
        canvas = self.canvas_grafico
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 240)
        dark = ctk.get_appearance_mode() == "Dark"
        bg = "#111827" if dark else "#FFFFFF"
        label_color = "#CBD5E1" if dark else "#334155"
        muted = "#64748B" if not dark else "#94A3B8"
        grid = "#1E293B" if dark else "#E2E8F0"
        accent = "#60A5FA" if dark else "#2563EB"
        quick = "#34D399" if dark else "#059669"
        canvas.configure(bg=bg)
        datos = self._datos_ventas_diarias
        if not datos:
            canvas.create_text(width/2, height/2, text="Todavía no hay ventas registradas", fill=muted, font=("Segoe UI", 11))
            return
        left, right, top, bottom = 42, 14, 18, 34
        pw, ph = width-left-right, height-top-bottom
        maxv = max(max(float(d.get("total") or 0), float(d.get("rapidas") or 0)) for d in datos) or 1
        # grid lines
        for i in range(4):
            y = top + ph * i / 3
            canvas.create_line(left, y, left+pw, y, fill=grid)
            val = maxv * (1-i/3)
            canvas.create_text(left-7, y, text=self._fmt(val).replace("$ ","$"), anchor="e", fill=muted, font=("Segoe UI", 8))
        step = pw / max(len(datos)-1, 1)
        points_total=[]; points_quick=[]
        for i,d in enumerate(datos):
            x=left+i*step
            total=float(d.get("total") or 0); q=float(d.get("rapidas") or 0)
            yt=top+ph-(total/maxv)*ph; yq=top+ph-(q/maxv)*ph
            points_total.append((x,yt)); points_quick.append((x,yq))
            if i % max(1, len(datos)//6) == 0 or i == len(datos)-1:
                label=str(d.get("dia", ""))[5:]
                canvas.create_text(x, height-12, text=label, fill=muted, font=("Segoe UI", 8))
        if len(points_total)>1: canvas.create_line(*[c for pt in points_total for c in pt], fill=accent, width=3, smooth=True)
        if len(points_quick)>1: canvas.create_line(*[c for pt in points_quick for c in pt], fill=quick, width=2, dash=(5,3), smooth=True)
        for x,y in points_total: canvas.create_oval(x-3,y-3,x+3,y+3,fill=accent,outline=accent)
        for x,y in points_quick: canvas.create_oval(x-2,y-2,x+2,y+2,fill=quick,outline=quick)
        canvas.create_text(left+4, 6, text="● Total", anchor="nw", fill=accent, font=("Segoe UI Semibold", 8))
        canvas.create_text(left+72, 6, text="● Rápidas", anchor="nw", fill=quick, font=("Segoe UI Semibold", 8))

    # --------------------------- Venta rápida ---------------------------
    def _construir_venta_rapida(self):
        view = self._new_view("Venta rápida")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        ctk.CTkLabel(header, text="Venta rápida", font=ctk.CTkFont(size=23, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Anotá solamente el monto. Sin clientes ni productos obligatorios.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(3, 0))

        main = ctk.CTkFrame(view, corner_radius=18, fg_color=("#FFFFFF", "#111827"))
        main.grid(row=1, column=0, sticky="ew")
        main.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main, text="Descripción (opcional)", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).grid(row=0, column=0, pady=(20, 3))
        self.entry_descripcion_rapida = ctk.CTkEntry(main, height=40, width=430, corner_radius=9, placeholder_text="Ej.: corte de pelo, café, venta de mostrador...")
        self.entry_descripcion_rapida.grid(row=1, column=0, padx=24, pady=(0, 10))
        ctk.CTkLabel(main, text="Monto de la venta", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=11)).grid(row=2, column=0, pady=(0, 4))
        self.entry_venta_rapida = ctk.CTkEntry(main, height=58, width=360, justify="center", font=ctk.CTkFont(size=26, weight="bold"), placeholder_text="$ 0,00")
        self.entry_venta_rapida.grid(row=3, column=0, padx=24, pady=(0, 14))
        self.entry_venta_rapida.bind("<Return>", lambda _e: self._registrar_venta_rapida())
        self.entry_venta_rapida.focus_set()

        presets = ctk.CTkFrame(main, fg_color="transparent")
        presets.grid(row=4, column=0, pady=(0, 12))
        for amount in (100, 200, 500, 1000, 2000):
            ctk.CTkButton(presets, text=f"$ {amount}", width=88, height=34, corner_radius=9, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=lambda a=amount: self._sumar_monto_rapido(a)).pack(side="left", padx=4)

        payment = ctk.CTkFrame(main, fg_color="transparent")
        payment.grid(row=5, column=0, pady=(0, 10))
        ctk.CTkLabel(payment, text="Pago", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 8))
        self.combo_pago_rapido = ctk.CTkComboBox(payment, values=["efectivo", "tarjeta", "transferencia"], width=145, height=36, corner_radius=8)
        self.combo_pago_rapido.set("efectivo")
        self.combo_pago_rapido.pack(side="left")

        actions = ctk.CTkFrame(main, fg_color="transparent")
        actions.grid(row=6, column=0, pady=(0, 24))
        ctk.CTkButton(actions, text="Limpiar", width=110, height=44, corner_radius=10, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=self._limpiar_venta_rapida).pack(side="left", padx=5)
        ctk.CTkButton(actions, text="Registrar venta  ↵", width=190, height=44, corner_radius=10, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, command=self._registrar_venta_rapida).pack(side="left", padx=5)

        recent = ctk.CTkFrame(view, corner_radius=18, fg_color=("#FFFFFF", "#111827"))
        recent.grid(row=2, column=0, sticky="nsew", pady=(18, 0))
        recent.grid_columnconfigure(0, weight=1)
        recent.grid_rowconfigure(1, weight=1)
        title_row = ctk.CTkFrame(recent, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=18, pady=15)
        ctk.CTkLabel(title_row, text="Ventas recientes", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.label_resumen_rapido = ctk.CTkLabel(title_row, text="Hoy: $ 0.00 · 0 ventas", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10))
        self.label_resumen_rapido.pack(side="right")
        self.tree_rapido = ttk.Treeview(recent, columns=("id", "fecha", "total", "metodo"), show="headings", style="Inventory.Treeview", height=7)
        for col, label, width in (("id", "Venta", 80), ("fecha", "Fecha", 180), ("total", "Monto", 150), ("metodo", "Pago", 140)):
            self.tree_rapido.heading(col, text=label)
            self.tree_rapido.column(col, width=width, anchor="center")
        self.tree_rapido.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        sb_rapido = ttk.Scrollbar(recent, orient="vertical", command=self.tree_rapido.yview)
        sb_rapido.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
        self.tree_rapido.configure(yscrollcommand=sb_rapido.set)

    def _sumar_monto_rapido(self, amount):
        current = self.entry_venta_rapida.get().strip().replace(",", ".")
        try:
            value = float(current) if current else 0.0
        except ValueError:
            value = 0.0
        self.entry_venta_rapida.delete(0, "end")
        self.entry_venta_rapida.insert(0, f"{value + amount:.2f}")
        self.entry_venta_rapida.focus_set()

    def _limpiar_venta_rapida(self):
        self.entry_venta_rapida.delete(0, "end")
        self.entry_descripcion_rapida.delete(0, "end")
        self.entry_venta_rapida.focus_set()

    def _registrar_venta_rapida(self):
        raw = self.entry_venta_rapida.get().strip().replace("$", "").replace(" ", "").replace(",", ".")
        try:
            total = float(raw)
            if total <= 0:
                raise ValueError
        except ValueError:
            self._warning("Monto inválido", "Escribí un monto mayor que 0.")
            self.entry_venta_rapida.focus_set()
            return
        try:
            pedido_id = self.db.registrar_venta_rapida(total, self.combo_pago_rapido.get(), self.entry_descripcion_rapida.get())
        except DatabaseError as e:
            self._error("No se pudo registrar", str(e))
            return
        self._limpiar_venta_rapida()
        self._cargar_pedidos()
        self._cargar_ventas_rapidas()
        self._actualizar_panel()
        self.label_resumen_rapido.configure(text=self._texto_resumen_rapido())

    def _texto_resumen_rapido(self):
        try:
            resumen = self.db.get_resumen_ventas()
            return f"Hoy: {self._fmt(resumen['total'])} · {resumen['cantidad']} ventas"
        except DatabaseError:
            return ""

    def _cargar_ventas_rapidas(self):
        if not hasattr(self, "tree_rapido"):
            return
        try:
            pedidos = self.db.get_pedidos()
            resumen = self.db.get_resumen_ventas()
        except DatabaseError:
            return
        for item in self.tree_rapido.get_children():
            self.tree_rapido.delete(item)
        for p in pedidos[:100]:
            metodo = "rápida" if not p.get("descripcion") and p["cliente"] == "Sin cliente" else (p.get("descripcion") or "venta de catálogo")
            self.tree_rapido.insert("", "end", values=(p["id"], p["fecha"], self._fmt(p["total"]), metodo))
        self.label_resumen_rapido.configure(text=f"Hoy: {self._fmt(resumen['total'])} · {resumen['cantidad']} ventas")

    # --------------------------- Almacén / Caja ---------------------------
    def _construir_almacen_caja(self):
        view = self._new_view("Almacén / Caja")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(header, text="Almacén / Caja", font=ctk.CTkFont(size=23, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="＋ Nueva venta", width=130, height=36, corner_radius=9,
                      fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
                      command=lambda: self._mostrar_vista("Pedidos")).pack(side="right")

        actions = ctk.CTkFrame(view, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for i in range(4): actions.grid_columnconfigure(i, weight=1)
        shortcuts = [
            ("🛒", "Nueva venta", "Abrir caja y cargar productos", "Pedidos"),
            ("⚡", "Venta rápida", "Cobrar sin crear un producto", "Venta rápida"),
            ("▤", "Productos", "Revisar precios y existencias", "Productos"),
            ("◒", "Rendimiento", "Ver ventas y movimiento", "Estadísticas"),
        ]
        for i, (icon, title, desc, target) in enumerate(shortcuts):
            card = ctk.CTkFrame(actions, corner_radius=15, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E2E8F0", "#1E293B"))
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 5 if i < 3 else 0))
            ctk.CTkLabel(card, text=icon, width=40, height=40, corner_radius=11, fg_color=("#EFF6FF", "#172033"), text_color=(COLOR_PRIMARY, "#93C5FD"), font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=14, pady=(13, 7))
            ctk.CTkLabel(card, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", padx=14)
            ctk.CTkLabel(card, text=desc, anchor="w", justify="left", wraplength=170, text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=9)).pack(fill="x", padx=14, pady=(2, 9))
            ctk.CTkButton(card, text="Abrir →", height=30, corner_radius=8, fg_color="transparent", hover_color=("#DBEAFE", "#1E3A5F"), text_color=(COLOR_PRIMARY, "#93C5FD"), command=lambda t=target: self._mostrar_vista(t)).pack(fill="x", padx=10, pady=(0, 10))

        body = ctk.CTkFrame(view, corner_radius=18, fg_color=("#FFFFFF", "#111827"))
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(body, text="Resumen de caja", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(18, 2), sticky="w")
        self.caja_resumen = ctk.CTkLabel(body, text="Cargando...", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10))
        self.caja_resumen.grid(row=0, column=1, padx=20, pady=(18, 2), sticky="e")
        self.tree_caja = ttk.Treeview(body, columns=("id", "fecha", "cliente", "total"), show="headings", style="Inventory.Treeview")
        for col, label, width in (("id", "Venta", 70), ("fecha", "Fecha", 170), ("cliente", "Cliente", 200), ("total", "Total", 120)):
            self.tree_caja.heading(col, text=label); self.tree_caja.column(col, width=width, anchor="w")
        self.tree_caja.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=14, pady=(8, 14))

    def _actualizar_almacen_caja(self):
        if not hasattr(self, "tree_caja"):
            return
        try:
            pedidos = self.db.get_pedidos()
            resumen = self.db.get_resumen_ventas()
        except DatabaseError:
            return
        for item in self.tree_caja.get_children(): self.tree_caja.delete(item)
        for p in pedidos[:10]:
            self.tree_caja.insert("", "end", values=(p["id"], p["fecha"], p["cliente"], self._fmt(p["total"])))
        self.caja_resumen.configure(text=f"Hoy · {resumen['cantidad']} ventas · {self._fmt(resumen['total'])}")

    # --------------------------- Inventario / Empresa ---------------------------
    def _construir_inventario_empresa(self):
        view = self._new_view("Inventario / Empresa")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(header, text="Inventario / Empresa", font=ctk.CTkFont(size=23, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Controlá la información completa del negocio desde un solo lugar.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).pack(side="left", padx=16, pady=(7,0))

        cards = ctk.CTkFrame(view, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for i in range(4): cards.grid_columnconfigure(i, weight=1)
        self.empresa_kpis = {}
        for i, (key, title, icon, target) in enumerate([
            ("productos", "Productos", "▤", "Productos"),
            ("clientes", "Clientes", "♙", "Clientes"),
            ("ventas", "Ventas", "↗", "Pedidos"),
            ("stats", "Estadísticas", "◒", "Estadísticas"),
        ]):
            card = ctk.CTkFrame(cards, corner_radius=15, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E2E8F0", "#1E293B"))
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 5 if i < 3 else 0))
            ctk.CTkLabel(card, text=icon, width=36, height=36, corner_radius=10, fg_color=("#EFF6FF", "#172033"), text_color=(COLOR_PRIMARY, "#93C5FD"), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(12,4))
            ctk.CTkLabel(card, text=title.upper(), text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=8, weight="bold")).pack(anchor="w", padx=14)
            value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=20, weight="bold")); value.pack(anchor="w", padx=14)
            self.empresa_kpis[key] = value
            ctk.CTkButton(card, text="Abrir →", height=28, corner_radius=8, fg_color="transparent", hover_color=("#DBEAFE", "#1E3A5F"), text_color=(COLOR_PRIMARY, "#93C5FD"), command=lambda t=target: self._mostrar_vista(t)).pack(fill="x", padx=9, pady=(3,9))

        body = ctk.CTkFrame(view, corner_radius=18, fg_color=("#FFFFFF", "#111827"))
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(body, text="Herramientas de gestión", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=(18,12), sticky="w")
        tools = [
            ("▤  Productos", "Precios, códigos, stock y servicios", "Productos"),
            ("♙  Clientes", "Contactos y datos de clientes", "Clientes"),
            ("◒  Estadísticas", "Ventas, margen, tendencias y stock", "Estadísticas"),
            ("⇅  Datos", "Importar, exportar y borrar datos de prueba", "Datos"),
        ]
        for i,(title,desc,target) in enumerate(tools):
            r=i//2+1; c=i%2
            card=ctk.CTkFrame(body,corner_radius=13,fg_color=("#F8FAFC","#0B1220"),border_width=1,border_color=("#E2E8F0","#1E293B"))
            card.grid(row=r,column=c,sticky="ew",padx=(18 if c==0 else 8,18 if c==1 else 8),pady=6)
            ctk.CTkLabel(card,text=title,anchor="w",font=ctk.CTkFont(size=12,weight="bold")).pack(fill="x",padx=14,pady=(12,2))
            ctk.CTkLabel(card,text=desc,anchor="w",text_color=("#64748B","#94A3B8"),font=ctk.CTkFont(size=9)).pack(fill="x",padx=14)
            ctk.CTkButton(card,text="Abrir",height=30,corner_radius=8,fg_color=COLOR_PRIMARY,hover_color=COLOR_PRIMARY_HOVER,command=lambda t=target:self._mostrar_vista(t)).pack(anchor="e",padx=12,pady=10)

    def _actualizar_inventario_empresa(self):
        if not hasattr(self, "empresa_kpis"):
            return
        try:
            productos=self.db.get_productos(); clientes=self.db.get_clientes(); pedidos=self.db.get_pedidos()
        except DatabaseError:
            return
        self.empresa_kpis["productos"].configure(text=str(len(productos)))
        self.empresa_kpis["clientes"].configure(text=str(len(clientes)))
        self.empresa_kpis["ventas"].configure(text=str(len(pedidos)))
        self.empresa_kpis["stats"].configure(text=self._fmt(self.db.get_resumen_ventas()["total"]))

    # --------------------------- Productos ---------------------------
    def _construir_productos(self):
        view = self._new_view("Productos")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)

        # Encabezado: la acción principal queda siempre visible.
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Productos", font=ctk.CTkFont(size=23, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Administrá tu inventario de forma simple.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ctk.CTkButton(
            header, text="＋  Agregar producto", width=190, height=42, corner_radius=10,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"), command=self._nuevo_producto
        ).grid(row=0, column=1, rowspan=2, padx=(15, 0))

        search = ctk.CTkEntry(view, height=40, corner_radius=9, placeholder_text="Buscar por nombre o categoría...")
        search.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        search.bind("<KeyRelease>", lambda _e: self._filtrar_tree(self.tree_productos, search.get(), 1, 2, 3, 4))

        table = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        table.grid(row=2, column=0, sticky="nsew")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        cols = ("id", "nombre", "tipo", "codigo", "categoria", "precio", "costo", "stock", "min")
        self.tree_productos = ttk.Treeview(table, columns=cols, show="headings", style="Inventory.Treeview")
        labels = {"id":"ID", "nombre":"Producto", "tipo":"Tipo", "codigo":"Código", "categoria":"Categoría", "precio":"Precio", "costo":"Costo", "stock":"Stock", "min":"Mín."}
        for col in cols:
            self.tree_productos.heading(col, text=labels[col])
            self.tree_productos.column(col, width=100, anchor="center")
        self.tree_productos.column("nombre", width=230, anchor="w")
        self.tree_productos.column("tipo", width=110, anchor="center")
        self.tree_productos.column("codigo", width=145, anchor="center")
        self.tree_productos.column("categoria", width=150, anchor="w")
        self.tree_productos.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        sb_productos = ttk.Scrollbar(table, orient="vertical", command=self.tree_productos.yview)
        sb_productos.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.tree_productos.configure(yscrollcommand=sb_productos.set)
        self.tree_productos.bind("<<TreeviewSelect>>", self._seleccionar_producto)
        self.tree_productos.bind("<Double-1>", lambda _e: self._editar_producto_seleccionado())

        # Barra de acciones debajo de la tabla. No depende de que el usuario
        # encuentre un formulario escondido en una columna lateral.
        actions = ctk.CTkFrame(view, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.prod_estado = ctk.CTkLabel(actions, text="Seleccioná un producto para editarlo.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10))
        self.prod_estado.pack(side="left")
        ctk.CTkButton(actions, text="Editar seleccionado", width=145, height=34, corner_radius=8, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=self._editar_producto_seleccionado).pack(side="right", padx=4)
        ctk.CTkButton(actions, text="Eliminar seleccionado", width=165, height=34, corner_radius=8, fg_color="transparent", hover_color=("#FEE2E2", "#3F1D1D"), text_color=(COLOR_DANGER, "#FCA5A5"), command=self._eliminar_producto).pack(side="right", padx=4)

    def _nuevo_producto(self):
        self._mostrar_formulario_producto()

    def _mostrar_formulario_producto(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Agregar producto" if self.prod_id_actual is None else "Editar producto")
        dialog.geometry("460x760")
        dialog.minsize(420, 700)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        title = "Agregar producto" if self.prod_id_actual is None else "Editar producto"
        ctk.CTkLabel(dialog, text=title, font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=28, pady=(25, 18), sticky="w")
        body = ctk.CTkFrame(dialog, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=28)
        body.grid_columnconfigure(0, weight=1)

        fields = [
            ("Nombre", "entry_prod_nombre"),
            ("Categoría", "entry_prod_categoria"),
            ("Tipo", "combo_prod_tipo"),
            ("Código de barras", "entry_prod_codigo"),
            ("Precio de venta", "entry_prod_precio"),
            ("Costo", "entry_prod_costo"),
            ("Stock actual", "entry_prod_stock"),
            ("Stock mínimo", "entry_prod_stock_min"),
        ]
        self._producto_dialog_entries = {}
        self._producto_dialog_rows = {}
        for row, (label, key) in enumerate(fields):
            lbl = ctk.CTkLabel(body, text=label, text_color=("#475569", "#94A3B8"), font=ctk.CTkFont(size=10))
            lbl.grid(row=row * 2, column=0, sticky="w", pady=(0, 4))
            if key == "combo_prod_tipo":
                widget = ctk.CTkComboBox(body, values=["Producto físico", "Servicio"], height=40, corner_radius=8, command=self._cambiar_tipo_producto_dialog)
                widget.set("Producto físico")
            else:
                widget = ctk.CTkEntry(body, height=40, corner_radius=8)
            widget.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 11))
            self._producto_dialog_entries[key] = widget
            self._producto_dialog_rows[key] = (lbl, widget)

        # Valores actuales o valores iniciales.
        if self.prod_id_actual is not None:
            sel = self.tree_productos.selection()
            if sel:
                values = self.tree_productos.item(sel[0], "values")
                mapping = {
                    "entry_prod_nombre": values[1],
                    "combo_prod_tipo": "Servicio" if values[2] == "Servicio" else "Producto físico",
                    "entry_prod_codigo": values[3] if values[3] != "—" else "",
                    "entry_prod_categoria": values[4] if values[4] != "—" else "",
                    "entry_prod_precio": values[5],
                    "entry_prod_costo": values[6],
                    "entry_prod_stock": values[7],
                    "entry_prod_stock_min": values[8],
                }
                for key, value in mapping.items():
                    widget = self._producto_dialog_entries[key]
                    if key == "combo_prod_tipo": widget.set(value)
                    else: widget.insert(0, value)
                if mapping["combo_prod_tipo"] == "Servicio":
                    self._cambiar_tipo_producto_dialog("Servicio")
        else:
            self._producto_dialog_entries["entry_prod_stock_min"].insert(0, "5")
            self._producto_dialog_entries["entry_prod_stock"].insert(0, "0")
            for key in ("entry_prod_nombre", "entry_prod_categoria", "entry_prod_codigo", "entry_prod_precio", "entry_prod_costo"):
                self._producto_dialog_entries[key].insert(0, "")

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=28, pady=(10, 24))
        buttons.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(buttons, text="Cancelar", height=42, corner_radius=9, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=dialog.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(buttons, text="Guardar producto", height=42, corner_radius=9, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=lambda: self._guardar_producto_dialog(dialog)).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._producto_dialog_entries["entry_prod_nombre"].focus_set()

    def _cambiar_tipo_producto_dialog(self, value):
        servicio = value == "Servicio"
        ocultar = ("entry_prod_codigo", "entry_prod_costo", "entry_prod_stock", "entry_prod_stock_min")
        for key, (label, widget) in self._producto_dialog_rows.items():
            if key in ocultar and servicio:
                label.grid_remove(); widget.grid_remove()
                if key != "entry_prod_costo":
                    widget.configure(state="disabled"); widget.delete(0, "end"); widget.insert(0, "0")
            elif key in ocultar:
                label.grid(); widget.grid(); widget.configure(state="normal")
        self._producto_dialog_entries["entry_prod_costo"].delete(0, "end")
        if servicio:
            self._producto_dialog_entries["entry_prod_costo"].insert(0, "0")
            self._producto_dialog_entries["entry_prod_codigo"].delete(0, "end")

    def _guardar_producto_dialog(self, dialog):
        e = self._producto_dialog_entries
        nombre = e["entry_prod_nombre"].get().strip()
        if not nombre:
            self._warning("Falta el nombre", "Escribí un nombre para el producto.", parent=dialog)
            return
        try:
            precio = float(e["entry_prod_precio"].get().replace(",", "."))
            costo = float(e["entry_prod_costo"].get().replace(",", "."))
            tipo = "servicio" if e["combo_prod_tipo"].get() == "Servicio" else "producto"
            stock = 0 if tipo == "servicio" else int(e["entry_prod_stock"].get())
            stock_min = 0 if tipo == "servicio" else int(e["entry_prod_stock_min"].get())
            if min(precio, costo, stock, stock_min) < 0:
                raise ValueError
        except ValueError:
            self._warning("Datos inválidos", "Precio, costo y stock deben ser números válidos.", parent=dialog)
            return
        categoria = e["entry_prod_categoria"].get().strip()
        codigo = "" if tipo == "servicio" else e["entry_prod_codigo"].get().strip()
        try:
            if self.prod_id_actual is None:
                self.db.add_producto(nombre, categoria, precio, costo, stock, stock_min, tipo, codigo)
            else:
                self.db.update_producto(self.prod_id_actual, nombre, categoria, precio, costo, stock, stock_min, tipo, codigo)
        except DatabaseError as exc:
            self._error("No se pudo guardar", str(exc), parent=dialog)
            return
        dialog.destroy()
        self.prod_id_actual = None
        self._cargar_productos()
        self._actualizar_panel()
        self.prod_estado.configure(text="Producto guardado correctamente.", text_color=(COLOR_SUCCESS, "#86EFAC"))

    def _editar_producto_seleccionado(self):
        if self.prod_id_actual is None:
            selection = self.tree_productos.selection()
            if not selection:
                self._info("Nada seleccionado", "Seleccioná un producto para editarlo.")
                return
            self._seleccionar_producto(None)
        self._mostrar_formulario_producto()

    def _limpiar_form_producto(self):
        self.prod_id_actual = None
        self.prod_estado.configure(text="Seleccioná un producto para editarlo.", text_color=("#64748B", "#94A3B8"))
        self._deseleccionar(self.tree_productos)

    def _eliminar_producto(self):
        if self.prod_id_actual is None:
            selection = self.tree_productos.selection()
            if not selection:
                self._info("Nada seleccionado", "Seleccioná un producto de la lista.")
                return
            self._seleccionar_producto(None)
        if not self._dialogo_confirmacion("Eliminar producto", "¿Querés eliminar el producto seleccionado?"):
            return
        try:
            self.db.delete_producto(self.prod_id_actual)
        except DatabaseError as e:
            self._error("No se pudo eliminar", str(e))
            return
        self._limpiar_form_producto()
        self._cargar_productos()
        self._actualizar_panel()

    def _seleccionar_producto(self, _event):
        selection = self.tree_productos.selection()
        if not selection:
            return
        values = self.tree_productos.item(selection[0], "values")
        self.prod_id_actual = int(values[0])
        self.prod_estado.configure(text=f"Producto seleccionado: {values[1]}", text_color=("#475569", "#CBD5E1"))

    # --------------------------- Clientes ---------------------------
    def _construir_clientes(self):
        view = self._new_view("Clientes")
        view.grid_columnconfigure(1, weight=1)
        view.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(view, width=290, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        form.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        form.grid_propagate(False)
        ctk.CTkLabel(form, text="Cliente", font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w", padx=20, pady=(22, 3))
        self.cli_estado = ctk.CTkLabel(form, text="Nuevo cliente", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10))
        self.cli_estado.pack(anchor="w", padx=20, pady=(0, 18))
        self.entry_cli_nombre = self._campo(form, "Nombre")
        self.entry_cli_telefono = self._campo(form, "Teléfono")
        self.entry_cli_email = self._campo(form, "Email")
        self.entry_cli_direccion = self._campo(form, "Dirección")
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=14)
        ctk.CTkButton(actions, text="Guardar", height=40, corner_radius=9, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=self._guardar_cliente).pack(fill="x", pady=3)
        ctk.CTkButton(actions, text="Limpiar", height=38, corner_radius=9, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=self._limpiar_form_cliente).pack(fill="x", pady=3)
        ctk.CTkButton(actions, text="Eliminar seleccionado", height=36, corner_radius=9, fg_color="transparent", hover_color=("#FEE2E2", "#3F1D1D"), text_color=(COLOR_DANGER, "#FCA5A5"), command=self._eliminar_cliente).pack(fill="x", pady=3)

        search = ctk.CTkEntry(view, height=38, placeholder_text="Buscar cliente...")
        search.grid(row=0, column=1, sticky="ew", pady=(0, 12))
        search.bind("<KeyRelease>", lambda _e: self._filtrar_tree(self.tree_clientes, search.get(), 1, 2, 3))

        table = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        table.grid(row=1, column=1, sticky="nsew")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        cols = ("id", "nombre", "telefono", "email", "direccion")
        self.tree_clientes = ttk.Treeview(table, columns=cols, show="headings", style="Inventory.Treeview")
        labels = {"id":"ID", "nombre":"Nombre", "telefono":"Teléfono", "email":"Email", "direccion":"Dirección"}
        for col in cols:
            self.tree_clientes.heading(col, text=labels[col])
            self.tree_clientes.column(col, width=145, anchor="center")
        self.tree_clientes.column("nombre", width=210, anchor="w")
        self.tree_clientes.column("direccion", width=210, anchor="w")
        self.tree_clientes.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        sb_clientes = ttk.Scrollbar(table, orient="vertical", command=self.tree_clientes.yview)
        sb_clientes.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.tree_clientes.configure(yscrollcommand=sb_clientes.set)
        self.tree_clientes.bind("<<TreeviewSelect>>", self._seleccionar_cliente)

    def _limpiar_form_cliente(self):
        self.cli_id_actual = None
        self.cli_estado.configure(text="Nuevo cliente")
        for e in (self.entry_cli_nombre, self.entry_cli_telefono, self.entry_cli_email, self.entry_cli_direccion):
            e.delete(0, "end")
        self._deseleccionar(self.tree_clientes)

    def _guardar_cliente(self):
        nombre = self.entry_cli_nombre.get().strip()
        if not nombre:
            self._warning("Falta el nombre", "Escribí el nombre del cliente.")
            return
        values = [e.get().strip() for e in (self.entry_cli_telefono, self.entry_cli_email, self.entry_cli_direccion)]
        try:
            if self.cli_id_actual is None:
                self.db.add_cliente(nombre, *values)
            else:
                self.db.update_cliente(self.cli_id_actual, nombre, *values)
        except DatabaseError as e:
            self._error("No se pudo guardar", str(e))
            return
        self._limpiar_form_cliente()
        self._cargar_clientes()

    def _eliminar_cliente(self):
        if self.cli_id_actual is None:
            self._info("Nada seleccionado", "Seleccioná un cliente de la lista.")
            return
        if not self._dialogo_confirmacion("Eliminar cliente", "¿Querés eliminar el cliente seleccionado?"):
            return
        try:
            self.db.delete_cliente(self.cli_id_actual)
        except DatabaseError as e:
            self._error("No se pudo eliminar", str(e))
            return
        self._limpiar_form_cliente()
        self._cargar_clientes()

    def _seleccionar_cliente(self, _event):
        selection = self.tree_clientes.selection()
        if not selection:
            return
        values = self.tree_clientes.item(selection[0], "values")
        self.cli_id_actual = int(values[0])
        self.cli_estado.configure(text=f"Editando cliente #{self.cli_id_actual}")
        for entry, value in zip((self.entry_cli_nombre, self.entry_cli_telefono, self.entry_cli_email, self.entry_cli_direccion), values[1:]):
            entry.delete(0, "end")
            entry.insert(0, value)

    # --------------------------- Pedidos ---------------------------
    def _construir_pedidos(self):
        view = self._new_view("Pedidos")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)

        form = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        form.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for i, w in enumerate((3, 3, 1, 1)):
            form.grid_columnconfigure(i, weight=w)
        ctk.CTkLabel(form, text="Nueva venta", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")
        ctk.CTkLabel(form, text="Completá lo mínimo y agregá productos.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).grid(row=1, column=0, padx=18, pady=(0, 14), sticky="w")

        ctk.CTkLabel(form, text="Cliente", font=ctk.CTkFont(size=10)).grid(row=0, column=1, padx=8, pady=(16, 4), sticky="w")
        self.combo_cliente = ctk.CTkComboBox(form, values=["(sin cliente)"], height=38, corner_radius=8)
        self.combo_cliente.grid(row=1, column=1, padx=8, pady=(0, 16), sticky="ew")
        ctk.CTkLabel(form, text="Producto", font=ctk.CTkFont(size=10)).grid(row=0, column=2, padx=8, pady=(16, 4), sticky="w")
        self.combo_producto = ctk.CTkComboBox(form, values=[], height=38, corner_radius=8)
        self.combo_producto.grid(row=1, column=2, padx=8, pady=(0, 16), sticky="ew")
        ctk.CTkLabel(form, text="Cantidad", font=ctk.CTkFont(size=10)).grid(row=0, column=3, padx=8, pady=(16, 4), sticky="w")
        self.entry_cantidad = ctk.CTkEntry(form, height=38, corner_radius=8)
        self.entry_cantidad.insert(0, "1")
        self.entry_cantidad.grid(row=1, column=3, padx=8, pady=(0, 16), sticky="ew")
        ctk.CTkButton(form, text="Agregar", height=38, width=110, corner_radius=8, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=self._agregar_item_pedido).grid(row=1, column=4, padx=(8, 18), pady=(0, 16))

        cart = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        cart.grid(row=2, column=0, sticky="nsew")
        cart.grid_rowconfigure(1, weight=1)
        cart.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cart, text="Carrito", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=18, pady=16, sticky="w")
        cols = ("producto", "cantidad", "precio", "subtotal")
        self.tree_carrito = ttk.Treeview(cart, columns=cols, show="headings", style="Inventory.Treeview")
        labels = {"producto":"Producto", "cantidad":"Cantidad", "precio":"Precio unit.", "subtotal":"Subtotal"}
        for col in cols:
            self.tree_carrito.heading(col, text=labels[col])
            self.tree_carrito.column(col, width=150, anchor="center")
        self.tree_carrito.column("producto", width=350, anchor="w")
        self.tree_carrito.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        footer = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.grid_columnconfigure(0, weight=1)
        self.label_total_pedido = ctk.CTkLabel(footer, text="Total  $ 0.00", font=ctk.CTkFont(size=21, weight="bold"))
        self.label_total_pedido.grid(row=0, column=0, padx=18, pady=16, sticky="w")
        ctk.CTkLabel(footer, text="Pago", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).grid(row=0, column=1, padx=(8, 4))
        self.combo_metodo_pago = ctk.CTkComboBox(footer, values=["efectivo", "tarjeta", "transferencia"], width=150, height=38, corner_radius=8)
        self.combo_metodo_pago.set("efectivo")
        self.combo_metodo_pago.grid(row=0, column=2, padx=4)
        ctk.CTkButton(footer, text="Vaciar", height=38, width=95, corner_radius=8, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), command=self._vaciar_carrito).grid(row=0, column=3, padx=5)
        ctk.CTkButton(footer, text="Quitar seleccionado", height=38, width=135, corner_radius=8, fg_color="transparent", hover_color=("#FEE2E2", "#3F1D1D"), text_color=(COLOR_DANGER, "#FCA5A5"), command=self._quitar_item_carrito).grid(row=0, column=4, padx=5)
        ctk.CTkButton(footer, text="Confirmar venta", height=38, width=145, corner_radius=8, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, command=self._confirmar_pedido).grid(row=0, column=5, padx=(5, 18))

        history = ctk.CTkFrame(view, corner_radius=14, fg_color=("#FFFFFF", "#111827"))
        history.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        history.grid_columnconfigure(0, weight=1)
        history.grid_rowconfigure(1, weight=1)
        header_history = ctk.CTkFrame(history, fg_color="transparent")
        header_history.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=10)
        header_history.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header_history, text="Registros de ventas", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        self.search_pedidos = ctk.CTkEntry(header_history, width=260, height=34, corner_radius=8, placeholder_text="Buscar por ID, cliente o estado...")
        self.search_pedidos.grid(row=0, column=1, sticky="e")
        self.search_pedidos.bind("<KeyRelease>", lambda _e: self._filtrar_tree(self.tree_pedidos, self.search_pedidos.get(), 0, 1, 2, 3, 4))
        self.tree_pedidos = ttk.Treeview(history, columns=("id", "cliente", "fecha", "estado", "total"), show="headings", height=10, style="Inventory.Treeview")
        for col, label in (("id", "Pedido"), ("cliente", "Cliente"), ("fecha", "Fecha"), ("estado", "Estado"), ("total", "Total")):
            self.tree_pedidos.heading(col, text=label)
            self.tree_pedidos.column(col, width=130, anchor="center")
        self.tree_pedidos.column("cliente", width=240, anchor="w")
        self.tree_pedidos.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        sb_pedidos = ttk.Scrollbar(history, orient="vertical", command=self.tree_pedidos.yview)
        sb_pedidos.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
        self.tree_pedidos.configure(yscrollcommand=sb_pedidos.set)
        ctk.CTkButton(history, text="Eliminar venta seleccionada", width=190, height=34, corner_radius=8, fg_color="transparent", hover_color=("#FEE2E2", "#3F1D1D"), text_color=(COLOR_DANGER, "#FCA5A5"), command=self._eliminar_pedido).grid(row=2, column=0, padx=18, pady=(0, 14), sticky="w")
        self.tree_pedidos.bind("<<TreeviewSelect>>", lambda _e: None)

    def _agregar_item_pedido(self):
        nombre = self.combo_producto.get()
        producto = self._mapa_productos.get(nombre)
        if not producto:
            self._warning("Elegí un producto", "Primero agregá un producto al inventario.")
            return
        try:
            cantidad = int(self.entry_cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            self._warning("Cantidad inválida", "Usá un número entero mayor que 0.")
            return
        es_servicio = producto.get("tipo") == "servicio"
        reservado = sum(it["cantidad"] for it in self._carrito if it["producto_id"] == producto["id"])
        disponible = None if es_servicio else int(producto["stock_actual"]) - reservado
        if disponible is not None and cantidad > disponible:
            self._warning("Stock insuficiente", f"Hay {disponible} unidades disponibles.")
            return
        existente = next((it for it in self._carrito if it["producto_id"] == producto["id"]), None)
        if existente:
            existente["cantidad"] += cantidad
        else:
            self._carrito.append({"producto_id": producto["id"], "nombre": nombre, "cantidad": cantidad, "precio_unitario": float(producto["precio"])})
        self._refrescar_carrito()
        self.entry_cantidad.delete(0, "end")
        self.entry_cantidad.insert(0, "1")

    def _refrescar_carrito(self):
        for i in self.tree_carrito.get_children():
            self.tree_carrito.delete(i)
        total = 0
        for it in self._carrito:
            subtotal = it["cantidad"] * it["precio_unitario"]
            total += subtotal
            self.tree_carrito.insert("", "end", values=(it["nombre"], it["cantidad"], self._fmt(it["precio_unitario"]), self._fmt(subtotal)))
        self.label_total_pedido.configure(text=f"Total  {self._fmt(total)}")

    def _vaciar_carrito(self):
        self._carrito = []
        self._refrescar_carrito()

    def _quitar_item_carrito(self):
        selection = self.tree_carrito.selection()
        if not selection:
            self._info("Nada seleccionado", "Seleccioná un producto del carrito para quitarlo.")
            return
        index = self.tree_carrito.index(selection[0])
        if 0 <= index < len(self._carrito):
            self._carrito.pop(index)
            self._refrescar_carrito()

    def _eliminar_pedido(self):
        selection = self.tree_pedidos.selection()
        if not selection:
            self._info("Nada seleccionado", "Seleccioná una venta de la lista.")
            return
        values = self.tree_pedidos.item(selection[0], "values")
        pedido_id = int(values[0])
        if not self._dialogo_confirmacion("Eliminar venta", "¿Querés eliminar esta venta? Si contenía productos, su stock será devuelto."):
            return
        try:
            self.db.delete_pedido(pedido_id)
        except DatabaseError as e:
            self._error("No se pudo eliminar", str(e))
            return
        self._cargar_todo()
        self._cargar_ventas_rapidas()

    def _confirmar_pedido(self):
        if not self._carrito:
            self._info("Carrito vacío", "Agregá al menos un producto.")
            return
        cliente = self.combo_cliente.get()
        cliente_id = None if cliente == "(sin cliente)" else self._mapa_clientes.get(cliente)
        total = sum(it["cantidad"] * it["precio_unitario"] for it in self._carrito)
        try:
            pedido_id = self.db.crear_pedido(cliente_id, self._carrito)
            self.db.registrar_pago(pedido_id, total, self.combo_metodo_pago.get())
        except DatabaseError as e:
            self._error("No se pudo confirmar", str(e))
            self._cargar_productos()
            self._cargar_pedidos()
            return
        self._vaciar_carrito()
        self._cargar_todo()
        self._info("Venta registrada", f"La venta #{pedido_id} quedó registrada correctamente.")

    # --------------------------- Estadísticas ---------------------------
    def _construir_estadisticas(self):
        view = self._new_view("Estadísticas")
        view.grid_columnconfigure(0, weight=1); view.grid_rowconfigure(1, weight=1)
        header=ctk.CTkFrame(view, fg_color="transparent"); header.grid(row=0,column=0,sticky="ew",pady=(0,10))
        ctk.CTkLabel(header,text="Estadísticas",font=ctk.CTkFont(size=23,weight="bold")).pack(side="left")
        ctk.CTkLabel(header,text="Ventas, stock, clientes y rendimiento.",text_color=("#64748B","#94A3B8"),font=ctk.CTkFont(size=10)).pack(side="left",padx=14,pady=(7,0))
        self.stats_comparacion = ctk.CTkLabel(header,text="Comparando...",text_color=("#64748B","#94A3B8"),font=ctk.CTkFont(size=9,weight="bold"))
        self.stats_comparacion.pack(side="left",padx=8,pady=(7,0))
        self.stats_periodo = ctk.CTkSegmentedButton(header, values=["7 días","30 días","90 días"], width=260, command=self._cambiar_periodo_stats)
        self.stats_periodo.set("30 días"); self.stats_periodo.pack(side="right",padx=(10,0))
        ctk.CTkButton(header,text="↻ Actualizar",width=105,height=34,corner_radius=9,fg_color=COLOR_PRIMARY,hover_color=COLOR_PRIMARY_HOVER,command=self._actualizar_estadisticas).pack(side="right")

        scroll=ctk.CTkScrollableFrame(view, fg_color="transparent")
        scroll.grid(row=1,column=0,sticky="nsew")
        scroll.grid_columnconfigure(0,weight=1); scroll.grid_columnconfigure(1,weight=1)
        self.stats_scroll=scroll

        kpi_frame=ctk.CTkFrame(scroll,fg_color="transparent")
        kpi_frame.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,10))
        for i in range(4): kpi_frame.grid_columnconfigure(i,weight=1)
        self.stats_labels={}
        kpis=[
            ("facturacion","Facturación","$","Ingresos del período"),("ventas","Ventas","↗","Operaciones registradas"),
            ("ticket","Ticket promedio","◉","Promedio por venta"),("unidades","Unidades","▤","Productos vendidos"),
            ("rapidas","Ventas rápidas","⚡","Cobros sin producto"),("margen","Margen estimado","◈","Productos con costo"),
            ("clientes","Clientes activos","♙","Clientes con compras"),("stock_bajo","Stock bajo","!","Productos para reponer"),
        ]
        for i,(key,title,icon,caption) in enumerate(kpis):
            r=i//4;c=i%4
            card=ctk.CTkFrame(kpi_frame,corner_radius=15,fg_color=("#FFFFFF","#111827"),border_width=1,border_color=("#E2E8F0","#263244"))
            card.grid(row=r,column=c,sticky="ew",padx=(0 if c==0 else 5,5 if c<3 else 0),pady=5)
            ctk.CTkLabel(card,text=icon,width=34,height=34,corner_radius=10,fg_color=("#EFF6FF","#172033"),text_color=(COLOR_PRIMARY,"#93C5FD"),font=ctk.CTkFont(size=15,weight="bold")).pack(anchor="w",padx=14,pady=(11,4))
            ctk.CTkLabel(card,text=title.upper(),text_color=("#64748B","#94A3B8"),font=ctk.CTkFont(size=8,weight="bold")).pack(anchor="w",padx=14)
            val=ctk.CTkLabel(card,text="0",font=ctk.CTkFont(size=20,weight="bold"));val.pack(anchor="w",padx=14)
            ctk.CTkLabel(card,text=caption,text_color=("#94A3B8","#64748B"),font=ctk.CTkFont(size=8)).pack(anchor="w",padx=14,pady=(0,11))
            self.stats_labels[key]=val

        # Main revenue chart
        chart=ctk.CTkFrame(scroll,corner_radius=16,fg_color=("#FFFFFF","#111827"))
        chart.grid(row=1,column=0,sticky="nsew",padx=(0,5),pady=5);chart.grid_rowconfigure(1,weight=1);chart.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(chart,text="Evolución de facturación",anchor="w",font=ctk.CTkFont(size=14,weight="bold")).grid(row=0,column=0,padx=18,pady=(15,2),sticky="w")
        self.stats_chart_hint=ctk.CTkLabel(chart,text="Total · catálogo · ventas rápidas",anchor="w",text_color=("#64748B","#94A3B8"),font=ctk.CTkFont(size=9));self.stats_chart_hint.grid(row=0,column=0,padx=18,pady=(37,6),sticky="w")
        self.canvas_stats=tk.Canvas(chart,highlightthickness=0,bd=0,bg="#FFFFFF",height=280);self.canvas_stats.grid(row=1,column=0,sticky="ew",padx=10,pady=(0,12));self.canvas_stats.bind("<Configure>",lambda _e:self._dibujar_stats())

        pay=ctk.CTkFrame(scroll,corner_radius=16,fg_color=("#FFFFFF","#111827"));pay.grid(row=1,column=1,sticky="nsew",padx=(5,0),pady=5);pay.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(pay,text="Métodos de pago",anchor="w",font=ctk.CTkFont(size=14,weight="bold")).grid(row=0,column=0,padx=18,pady=(15,8),sticky="w")
        self.stats_pagos_frame=ctk.CTkFrame(pay,fg_color="transparent");self.stats_pagos_frame.grid(row=1,column=0,sticky="nsew",padx=12,pady=4)

        top=ctk.CTkFrame(scroll,corner_radius=16,fg_color=("#FFFFFF","#111827"));top.grid(row=2,column=0,sticky="nsew",padx=(0,5),pady=5);top.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(top,text="Productos que más se venden",anchor="w",font=ctk.CTkFont(size=14,weight="bold")).grid(row=0,column=0,padx=18,pady=(15,8),sticky="w")
        self.stats_top_frame=ctk.CTkFrame(top,fg_color="transparent");self.stats_top_frame.grid(row=1,column=0,sticky="ew",padx=12,pady=(0,12))

        low=ctk.CTkFrame(scroll,corner_radius=16,fg_color=("#FFFFFF","#111827"));low.grid(row=2,column=1,sticky="nsew",padx=(5,0),pady=5);low.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(low,text="Alertas de stock",anchor="w",font=ctk.CTkFont(size=14,weight="bold")).grid(row=0,column=0,padx=18,pady=(15,8),sticky="w")
        self.stats_low_frame=ctk.CTkFrame(low,fg_color="transparent");self.stats_low_frame.grid(row=1,column=0,sticky="ew",padx=12,pady=(0,12))

        insights=ctk.CTkFrame(scroll,corner_radius=16,fg_color=("#FFFFFF","#111827"));insights.grid(row=3,column=0,columnspan=2,sticky="ew",pady=5);insights.grid_columnconfigure(0,weight=1);insights.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(insights,text="Lecturas útiles del negocio",anchor="w",font=ctk.CTkFont(size=14,weight="bold")).grid(row=0,column=0,columnspan=2,padx=18,pady=(15,8),sticky="w")
        self.stats_insights=ctk.CTkLabel(insights,text="",anchor="w",justify="left",wraplength=950,text_color=("#475569","#CBD5E1"),font=ctk.CTkFont(size=10));self.stats_insights.grid(row=1,column=0,columnspan=2,padx=18,pady=(0,16),sticky="w")
        self._stats_data={}

    def _cambiar_periodo_stats(self, _value=None):
        self._actualizar_estadisticas()

    def _stats_days(self):
        return {"7 días":7,"30 días":30,"90 días":90}.get(self.stats_periodo.get(),30)

    def _clear_frame(self, frame):
        for child in frame.winfo_children(): child.destroy()

    def _actualizar_estadisticas(self):
        if not hasattr(self,"stats_labels"): return
        try: data=self.db.get_estadisticas(self._stats_days())
        except DatabaseError as e: self._error("No se pudieron calcular las estadísticas",str(e));return
        self._stats_data=data; k=data["kpis"]; prev=float(k.get("periodo_anterior") or 0); current=float(k.get("facturacion") or 0)
        growth=((current-prev)/prev*100) if prev else (100.0 if current else 0.0)
        values={"facturacion":self._fmt(current),"ventas":str(int(k.get("ventas") or 0)),"ticket":self._fmt(k.get("ticket_promedio")),"unidades":str(int(k.get("unidades") or 0)),"rapidas":f"{int(k.get('ventas_rapidas') or 0)} · {self._fmt(k.get('facturacion_rapida'))}","margen":self._fmt(k.get("margen_estimado")),"clientes":str(int(k.get("clientes_activos") or 0)),"stock_bajo":str(len(data.get("stock_bajo",[])))}
        if hasattr(self, "stats_comparacion"):
            self.stats_comparacion.configure(text=f"{growth:+.1f}% vs. período anterior")
        for key,val in values.items(): self.stats_labels[key].configure(text=val)
        self._dibujar_stats()
        self._render_stats_lists()
        direction="subió" if growth>0.5 else "bajó" if growth<-0.5 else "se mantuvo estable"
        best=max(data.get("diarias",[]),key=lambda x:float(x.get("total") or 0),default=None)
        best_text=f"Mejor día: {best['dia']} · {self._fmt(best['total'])}. " if best else "Todavía no hay un día con ventas. "
        self.stats_insights.configure(text=f"La facturación {direction} {abs(growth):.1f}% frente al período anterior. {best_text}Stock valorizado a costo: {self._fmt(k.get('valor_stock_costo'))} · a precio de venta: {self._fmt(k.get('valor_stock_venta'))}. Servicios vendidos: {int(k.get('servicios') or 0)} · facturación de servicios: {self._fmt(k.get('facturacion_servicios'))}.")

    def _render_stats_lists(self):
        data=self._stats_data
        self._clear_frame(self.stats_pagos_frame); pagos=data.get("pagos",[]); maxp=max([float(x.get("monto") or 0) for x in pagos] or [1])
        if not pagos: ctk.CTkLabel(self.stats_pagos_frame,text="Sin pagos registrados en el período.",text_color=("#64748B","#94A3B8")).pack(pady=25)
        for x in pagos:
            row=ctk.CTkFrame(self.stats_pagos_frame,fg_color="transparent");row.pack(fill="x",pady=5)
            metodo=str(x.get("metodo") or "sin método").capitalize();m=float(x.get("monto") or 0)
            ctk.CTkLabel(row,text=f"{metodo} · {int(x.get('operaciones') or 0)}",width=145,anchor="w",font=ctk.CTkFont(size=10,weight="bold")).pack(side="left")
            bar=ctk.CTkProgressBar(row,height=8,corner_radius=4,progress_color=(COLOR_PRIMARY,"#60A5FA"));bar.pack(side="left",fill="x",expand=True,padx=8);bar.set(m/maxp)
            ctk.CTkLabel(row,text=self._fmt(m),width=90,anchor="e",font=ctk.CTkFont(size=10)).pack(side="right")
        self._clear_frame(self.stats_top_frame); top=data.get("top_productos",[])
        if not top: ctk.CTkLabel(self.stats_top_frame,text="No hay productos vendidos en el período.",text_color=("#64748B","#94A3B8")).pack(pady=25)
        for i,x in enumerate(top,1):
            row=ctk.CTkFrame(self.stats_top_frame,fg_color=("#F8FAFC","#0B1220"),corner_radius=9);row.pack(fill="x",pady=3)
            ctk.CTkLabel(row,text=f"{i}",width=28,text_color=(COLOR_PRIMARY,"#93C5FD"),font=ctk.CTkFont(size=10,weight="bold")).pack(side="left",padx=(8,3))
            ctk.CTkLabel(row,text=x["nombre"],anchor="w",font=ctk.CTkFont(size=10,weight="bold")).pack(side="left",fill="x",expand=True)
            ctk.CTkLabel(row,text=f"{int(x['unidades'])} uds · {self._fmt(x['facturacion'])}",text_color=("#64748B","#CBD5E1"),font=ctk.CTkFont(size=9)).pack(side="right",padx=10)
        self._clear_frame(self.stats_low_frame); low=data.get("stock_bajo",[])
        if not low: ctk.CTkLabel(self.stats_low_frame,text="✓ No hay productos bajo el mínimo.",text_color=(COLOR_SUCCESS,"#86EFAC")).pack(pady=25)
        for x in low:
            row=ctk.CTkFrame(self.stats_low_frame,fg_color=("#FEF2F2","#2A1518"),corner_radius=9);row.pack(fill="x",pady=3)
            ctk.CTkLabel(row,text="!",width=24,text_color=(COLOR_WARNING,"#FBBF24"),font=ctk.CTkFont(size=11,weight="bold")).pack(side="left",padx=7)
            ctk.CTkLabel(row,text=x["nombre"],anchor="w",font=ctk.CTkFont(size=10,weight="bold")).pack(side="left",fill="x",expand=True)
            ctk.CTkLabel(row,text=f"{x['stock_actual']} / mín. {x['stock_minimo']}",text_color=("#B91C1C","#FCA5A5"),font=ctk.CTkFont(size=9)).pack(side="right",padx=10)

    def _dibujar_stats(self):
        if not hasattr(self,"canvas_stats"): return
        c=self.canvas_stats;c.delete("all");w=max(c.winfo_width(),500);h=max(c.winfo_height(),280);dark=ctk.get_appearance_mode()=="Dark";bg="#111827" if dark else "#FFFFFF";muted="#94A3B8" if dark else "#64748B";grid="#263244" if dark else "#E2E8F0";accent="#60A5FA" if dark else "#2563EB";quick="#34D399" if dark else "#059669";catalog="#A78BFA" if dark else "#7C3AED";c.configure(bg=bg)
        datos=self._stats_data.get("diarias",[]) if hasattr(self,"_stats_data") else []
        if not datos:c.create_text(w/2,h/2,text="Todavía no hay ventas registradas en este período",fill=muted,font=("Segoe UI",11));return
        left,right,top,bottom=52,20,24,38;pw,ph=w-left-right,h-top-bottom;mx=max([float(x.get("total") or 0) for x in datos] or [1]) or 1
        for i in range(5):
            y=top+ph*i/4;c.create_line(left,y,left+pw,y,fill=grid);c.create_text(left-8,y,text=self._fmt(mx*(1-i/4)).replace("$ ","$"),anchor="e",fill=muted,font=("Segoe UI",8))
        step=pw/max(len(datos)-1,1);pts=[];qpts=[];cpts=[]
        for i,d in enumerate(datos):
            x=left+i*step;t=float(d.get("total") or 0);q=float(d.get("rapidas") or 0);cat=max(0,t-q);pts.append((x,top+ph-(t/mx)*ph));qpts.append((x,top+ph-(q/mx)*ph));cpts.append((x,top+ph-(cat/mx)*ph))
            if i%max(1,len(datos)//7)==0 or i==len(datos)-1:c.create_text(x,h-14,text=str(d.get("dia",""))[5:],fill=muted,font=("Segoe UI",8))
        if len(pts)>1:
            c.create_line(*[v for p in pts for v in p],fill=accent,width=3,smooth=True);c.create_line(*[v for p in qpts for v in p],fill=quick,width=2,dash=(5,3),smooth=True);c.create_line(*[v for p in cpts for v in p],fill=catalog,width=2,dash=(2,3),smooth=True)
        c.create_text(left+3,7,text="● Total",anchor="nw",fill=accent,font=("Segoe UI Semibold",8));c.create_text(left+65,7,text="● Rápidas",anchor="nw",fill=quick,font=("Segoe UI Semibold",8));c.create_text(left+135,7,text="● Catálogo",anchor="nw",fill=catalog,font=("Segoe UI Semibold",8))

    # --------------------------- Datos ---------------------------
    def _construir_datos(self):
        view = self._new_view("Datos")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(view, text="Datos", font=ctk.CTkFont(size=23, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(view, text="Tus registros y copias de seguridad, organizados de forma clara.", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", pady=(3, 16))

        body = ctk.CTkFrame(view, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        records = ctk.CTkFrame(body, corner_radius=18, fg_color=("#FFFFFF", "#111827"))
        records.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        records.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(records, text="Registros de Inventory", anchor="w", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=22, pady=(22, 3), sticky="w")
        ctk.CTkLabel(records, text="Administrá rápidamente los datos que componen tu inventario.", anchor="w", text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).grid(row=1, column=0, padx=22, pady=(0, 18), sticky="w")

        cards = ctk.CTkFrame(records, fg_color="transparent")
        cards.grid(row=2, column=0, sticky="ew", padx=16)
        for i in range(3): cards.grid_columnconfigure(i, weight=1)
        self.datos_resumen = {}
        for i, (key, title, accent) in enumerate((("productos", "Productos", COLOR_PRIMARY), ("clientes", "Clientes", COLOR_SUCCESS), ("ventas", "Ventas", COLOR_WARNING))):
            card = ctk.CTkFrame(cards, corner_radius=12, fg_color=("#F8FAFC", "#0B1220"), border_width=1, border_color=("#E2E8F0", "#1E293B"))
            card.grid(row=0, column=i, sticky="ew", padx=5)
            ctk.CTkLabel(card, text=title.upper(), text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=9, weight="bold")).pack(anchor="w", padx=14, pady=(12, 1))
            label=ctk.CTkLabel(card, text="0", text_color=(accent, accent), font=ctk.CTkFont(size=22, weight="bold"))
            label.pack(anchor="w", padx=14, pady=(0, 12))
            self.datos_resumen[key]=label

        table_wrap = ctk.CTkFrame(records, fg_color="transparent")
        table_wrap.grid(row=3, column=0, sticky="nsew", padx=16, pady=16)
        records.grid_rowconfigure(3, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1); table_wrap.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(table_wrap, text="Actividad reciente", anchor="w", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w", padx=5, pady=(0, 8))
        self.tree_datos = ttk.Treeview(table_wrap, columns=("tipo","detalle","fecha"), show="headings", height=7, style="Inventory.Treeview")
        for col, label, width in (("tipo","Tipo",110),("detalle","Detalle",300),("fecha","Fecha",160)):
            self.tree_datos.heading(col, text=label); self.tree_datos.column(col, width=width, anchor="w")
        self.tree_datos.grid(row=1, column=0, sticky="nsew")

        actions = ctk.CTkFrame(body, corner_radius=18, fg_color=("#FFFFFF", "#111827"))
        actions.grid(row=0, column=1, sticky="new")
        ctk.CTkLabel(actions, text="Copias y respaldo", anchor="w", font=ctk.CTkFont(size=17, weight="bold")).pack(fill="x", padx=22, pady=(22, 4))
        ctk.CTkLabel(actions, text="Usá .inventory para mover o guardar una copia completa.", anchor="w", justify="left", wraplength=330, text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10)).pack(fill="x", padx=22, pady=(0, 20))
        ctk.CTkButton(actions, text="↑  Exportar datos", height=44, corner_radius=10, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, font=ctk.CTkFont(size=11, weight="bold"), command=self._exportar_datos).pack(fill="x", padx=22, pady=5)
        ctk.CTkButton(actions, text="↓  Importar datos", height=44, corner_radius=10, fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"), text_color=("#334155", "#E2E8F0"), font=ctk.CTkFont(size=11, weight="bold"), command=self._importar_datos).pack(fill="x", padx=22, pady=5)
        ctk.CTkButton(actions, text="⌫  Borrar todos los datos", height=44, corner_radius=10, fg_color=("#FEE2E2", "#3F1D1D"), hover_color=("#FECACA", "#5A2424"), text_color=(COLOR_DANGER, "#FCA5A5"), font=ctk.CTkFont(size=11, weight="bold"), command=self._borrar_datos).pack(fill="x", padx=22, pady=5)
        ctk.CTkLabel(actions, text="La importación crea un backup automático antes de reemplazar los datos.", anchor="w", justify="left", wraplength=320, text_color=("#94A3B8", "#64748B"), font=ctk.CTkFont(size=9)).pack(fill="x", padx=22, pady=(14, 22))
        self.label_archivo_datos = ctk.CTkLabel(actions, text="Sin operaciones recientes", anchor="w", wraplength=320, text_color=("#64748B", "#94A3B8"), font=ctk.CTkFont(size=10))
        self.label_archivo_datos.pack(fill="x", padx=22, pady=(0, 20))

        info = ctk.CTkFrame(body, corner_radius=18, fg_color=("#EFF6FF", "#0F1B32"), border_width=1, border_color=("#BFDBFE", "#1D4ED8"))
        info.grid(row=1, column=1, sticky="new", pady=(12,0))
        ctk.CTkLabel(info, text="💡 Consejo", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#1D4ED8", "#93C5FD")).pack(fill="x", padx=20, pady=(17,5))
        ctk.CTkLabel(info, text="Exportá una copia antes de hacer cambios importantes o trasladar Inventory a otra PC.", anchor="w", justify="left", wraplength=320, text_color=("#334155", "#CBD5E1"), font=ctk.CTkFont(size=10)).pack(fill="x", padx=20, pady=(0,18))

    def _actualizar_datos(self):
        try:
            productos = self.db.get_productos(); clientes = self.db.get_clientes(); pedidos = self.db.get_pedidos()
        except DatabaseError:
            return
        if hasattr(self, "datos_resumen"):
            self.datos_resumen["productos"].configure(text=str(len(productos)))
            self.datos_resumen["clientes"].configure(text=str(len(clientes)))
            self.datos_resumen["ventas"].configure(text=str(len(pedidos)))
        if hasattr(self, "tree_datos"):
            for item in self.tree_datos.get_children(): self.tree_datos.delete(item)
            for p in productos[:4]: self.tree_datos.insert("", "end", values=("Producto", p["nombre"], "Registro activo"))
            for c in clientes[:3]: self.tree_datos.insert("", "end", values=("Cliente", c["nombre"], "Registro activo"))
            for p in pedidos[:3]: self.tree_datos.insert("", "end", values=("Venta", f"Venta #{p['id']} · {self._fmt(p['total'])}", p["fecha"]))

    def _exportar_datos(self):
        ruta = filedialog.asksaveasfilename(
            title="Exportar datos", defaultextension=".inventory", initialfile="inventory_backup.inventory",
            filetypes=[("Inventory", "*.inventory"), ("Excel", "*.xlsx"), ("CSV", "*.csv"), ("Texto tabulado", "*.txt"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            self.db.exportar_datos(ruta)
        except DatabaseError as e:
            self._error("No se pudo exportar", str(e)); return
        self.label_archivo_datos.configure(text=f"Exportado: {Path(ruta).name}")
        self._success("Datos exportados", f"Se guardó {Path(ruta).name} correctamente.")

    def _importar_datos(self):
        ruta = filedialog.askopenfilename(
            title="Importar datos",
            filetypes=[("Inventory", "*.inventory"), ("Excel", "*.xlsx"), ("CSV", "*.csv"), ("Texto tabulado", "*.txt"), ("SQLite", "*.db *.sqlite *.sqlite3"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        if not self._dialogo_confirmacion("Reemplazar datos", "La importación reemplazará los datos actuales. Antes se creará un backup .inventory. ¿Querés continuar?"):
            return
        backup = Path(self.db.ruta).with_name(f"inventory_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.inventory")
        try:
            self.db.exportar_datos(backup)
            resumen = self.db.importar_archivo(ruta)
        except DatabaseError as e:
            self._error("No se pudo importar", str(e)); return
        self._cargar_todo()
        self.label_archivo_datos.configure(text=f"Importado: {Path(ruta).name}")
        partes = [f"{k}: {v}" for k, v in resumen.items() if isinstance(v, int)]
        detalle = " · ".join(partes) if partes else "Archivo procesado correctamente."
        self._success("Datos importados", f"{detalle}. Backup automático creado.")

    def _borrar_datos(self):
        mensaje=("Esta acción va a eliminar productos, clientes, ventas, pagos y movimientos. "
                 "Se creará automáticamente una copia .inventory antes de borrar todo. "
                 "¿Querés continuar?")
        if not self._dialogo_confirmacion("Borrar todos los datos", mensaje): return
        backup=Path(self.db.ruta).with_name(f"inventory_before_delete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.inventory")
        try:
            self.db.exportar_datos(backup)
            self.db.borrar_todos_los_datos()
        except DatabaseError as e:
            self._error("No se pudieron borrar los datos",str(e));return
        self._cargar_todo()
        self._success("Datos borrados",f"La base quedó vacía. Backup creado: {backup.name}")

    def _cargar_todo(self):
        self._cargar_productos()
        self._cargar_clientes()
        self._cargar_pedidos()
        self._cargar_ventas_rapidas()
        self._actualizar_panel()
        self._actualizar_datos()
        self._actualizar_estadisticas()

    def _cargar_productos(self):
        try:
            productos = self.db.get_productos()
        except DatabaseError as e:
            self._error("Error", str(e))
            return
        for item in self.tree_productos.get_children():
            self.tree_productos.delete(item)
        for p in productos:
            self.tree_productos.insert("", "end", values=(p["id"], p["nombre"], "Servicio" if p.get("tipo") == "servicio" else "Producto", p.get("codigo_barra") or "—", p["categoria"] or "—", self._fmt(p["precio"]), self._fmt(p["costo"]), "—" if p.get("tipo") == "servicio" else p["stock_actual"], "—" if p.get("tipo") == "servicio" else p["stock_minimo"]))
        self._mapa_productos = {p["nombre"]: p for p in productos}
        nombres = list(self._mapa_productos)
        self.combo_producto.configure(values=nombres)
        if nombres:
            self.combo_producto.set(nombres[0])
        else:
            self.combo_producto.set("")

    def _cargar_clientes(self):
        try:
            clientes = self.db.get_clientes()
        except DatabaseError as e:
            self._error("Error", str(e))
            return
        for item in self.tree_clientes.get_children():
            self.tree_clientes.delete(item)
        for c in clientes:
            self.tree_clientes.insert("", "end", values=(c["id"], c["nombre"], c["telefono"] or "—", c["email"] or "—", c["direccion"] or "—"))
        self._mapa_clientes = {c["nombre"]: c["id"] for c in clientes}
        names = ["(sin cliente)"] + list(self._mapa_clientes)
        self.combo_cliente.configure(values=names)
        self.combo_cliente.set(names[0])

    def _cargar_pedidos(self):
        try:
            pedidos = self.db.get_pedidos()
        except DatabaseError as e:
            self._error("Error", str(e))
            return
        for item in self.tree_pedidos.get_children():
            self.tree_pedidos.delete(item)
        for p in pedidos[:200]:
            self.tree_pedidos.insert("", "end", values=(p["id"], p["cliente"], p["fecha"], p["estado"].capitalize(), self._fmt(p["total"])))

    def _filtrar_tree(self, tree, query, *columns):
        q = query.strip().lower()
        for item in tree.get_children():
            tree.reattach(item, "", "end")
            values = tree.item(item, "values")
            if q and not any(q in str(values[i]).lower() for i in columns if i < len(values)):
                tree.detach(item)

    def _deseleccionar(self, tree):
        for item in tree.selection():
            tree.selection_remove(item)

    @staticmethod
    def _fmt(value):
        try:
            return f"$ {float(value):,.2f}"
        except (TypeError, ValueError):
            return "$ 0.00"

    def _cerrar(self):
        try:
            self.db.close()
        finally:
            self.destroy()


def main():
    app = InventoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
