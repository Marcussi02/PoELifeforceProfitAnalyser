import tkinter as tk
import time
from threading import Thread
from tkinter import messagebox, ttk

import requests

from poe_analyzer import analyze_lifeforce


class LifeforceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PoE Lifeforce Value Checker")
        self.root.geometry("1080x430")

        self.league_var = tk.StringVar(value="Mirage")
        self.amount_var = tk.StringVar(value="50000")
        self.chaos_per_divine_var = tk.StringVar(value="330")
        self.divine_rate_source_var = tk.StringVar(value="manual")
        self.status_var = tk.StringVar(value="Ready")
        self.is_loading = False
        self.cache_ttl_seconds = 45
        self.cache: dict[tuple[str, float, float | None], tuple[float, dict]] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="League:").pack(side=tk.LEFT)
        ttk.Entry(top, width=20, textvariable=self.league_var).pack(side=tk.LEFT, padx=(6, 12))

        ttk.Label(top, text="Amount:").pack(side=tk.LEFT)
        ttk.Entry(top, width=12, textvariable=self.amount_var).pack(side=tk.LEFT, padx=(6, 12))

        ttk.Label(top, text="Chaos/Divine:").pack(side=tk.LEFT)
        self.chaos_per_divine_entry = ttk.Entry(top, width=10, textvariable=self.chaos_per_divine_var)
        self.chaos_per_divine_entry.pack(side=tk.LEFT, padx=(6, 12))

        ttk.Radiobutton(
            top,
            text="Manual Rate",
            value="manual",
            variable=self.divine_rate_source_var,
            command=self._on_rate_source_changed,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Radiobutton(
            top,
            text="poe.ninja Rate",
            value="poeninja",
            variable=self.divine_rate_source_var,
            command=self._on_rate_source_changed,
        ).pack(side=tk.LEFT, padx=(0, 12))

        self.refresh_button = ttk.Button(top, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side=tk.LEFT)

        self.loading_label = ttk.Label(top, text="Loading...")

        self.market_label = ttk.Label(self.root, text="Currency Exchange Rate: -", padding=(12, 0))
        self.market_label.pack(anchor="w")

        columns = (
            "type",
            "lifeforce_per_chaos",
            "lifeforce_per_divine",
            "chaos_per_lifeforce",
            "chaos_for_amount",
            "whole_divine",
            "chaos_left",
            "recommendation",
        )
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=10)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        self.tree.heading("type", text="Type")
        self.tree.heading("lifeforce_per_chaos", text="LF / Chaos")
        self.tree.heading("lifeforce_per_divine", text="LF / Divine")
        self.tree.heading("chaos_per_lifeforce", text="Chaos / LF (from Divine)")
        self.tree.heading("chaos_for_amount", text="Chaos Out")
        self.tree.heading("whole_divine", text="Divine Out")
        self.tree.heading("chaos_left", text="Chaos Left")
        self.tree.heading("recommendation", text="Best Strategy")

        self.tree.column("type", width=90, anchor=tk.W)
        self.tree.column("lifeforce_per_chaos", width=120, anchor=tk.E)
        self.tree.column("lifeforce_per_divine", width=130, anchor=tk.E)
        self.tree.column("chaos_per_lifeforce", width=120, anchor=tk.E)
        self.tree.column("chaos_for_amount", width=100, anchor=tk.E)
        self.tree.column("whole_divine", width=100, anchor=tk.E)
        self.tree.column("chaos_left", width=100, anchor=tk.E)
        self.tree.column("recommendation", width=220, anchor=tk.CENTER)

        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 0, 12, 10)).pack(anchor="w")
        self._on_rate_source_changed()

    def _on_rate_source_changed(self) -> None:
        # Disable manual rate input when using poe.ninja rate.
        if self.divine_rate_source_var.get() == "manual":
            self.chaos_per_divine_entry.configure(state="normal")
        else:
            self.chaos_per_divine_entry.configure(state="disabled")

    def refresh(self) -> None:
        if self.is_loading:
            return

        league = self.league_var.get().strip() or "Standard"
        if not self.league_var.get().strip():
            self.league_var.set("Standard")

        try:
            amount = float(self.amount_var.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Amount must be a positive number.")
            return

        chaos_per_divine_override = None
        if self.divine_rate_source_var.get() == "manual":
            try:
                chaos_per_divine = float(self.chaos_per_divine_var.get())
                if chaos_per_divine <= 0:
                    raise ValueError
                chaos_per_divine_override = chaos_per_divine
            except ValueError:
                messagebox.showerror("Invalid Input", "Chaos/Divine must be a positive number.")
                return

        cache_key = (league, amount, chaos_per_divine_override)
        cached = self.cache.get(cache_key)
        if cached and (time.time() - cached[0] <= self.cache_ttl_seconds):
            self._apply_result(cached[1])
            self.status_var.set("Updated instantly from cache.")
            return

        self._set_loading(True)

        def worker() -> None:
            try:
                result = analyze_lifeforce(league, amount, chaos_per_divine_override)
                self.cache[cache_key] = (time.time(), result)
                self.root.after(0, lambda: self._on_fetch_success(result))
            except (requests.RequestException, ValueError) as exc:
                self.root.after(0, lambda: self._on_fetch_error(exc))

        Thread(target=worker, daemon=True).start()

    def _on_fetch_success(self, result: dict) -> None:
        self._apply_result(result)
        self.status_var.set("Updated successfully.")
        self._set_loading(False)

    def _on_fetch_error(self, exc: Exception) -> None:
        self.status_var.set("Failed to load market data.")
        self._set_loading(False)
        messagebox.showerror("Fetch Error", str(exc))

    def _set_loading(self, is_loading: bool) -> None:
        self.is_loading = is_loading
        if is_loading:
            self.status_var.set("Loading market data...")
            self.refresh_button.configure(state="disabled")
            self.loading_label.pack(side=tk.LEFT, padx=(10, 0))
        else:
            self.refresh_button.configure(state="normal")
            self.loading_label.pack_forget()

    def _apply_result(self, result: dict) -> None:

        self.market_label.config(
            text=f"Currency Exchange Rate: 1 Divine ~= {result['chaos_per_divine']:.2f} Chaos "
            f"(source: {result['chaos_per_divine_source']}) |  League: {result['league']}  |  Amount: {result['amount']:,.0f}"
        )

        for row_id in self.tree.get_children():
            self.tree.delete(row_id)

        for row in result["rows"]:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["type"],
                    f"{row['lifeforce_per_chaos']:.4f}",
                    f"{row['lifeforce_per_divine']:.2f}",
                    f"{row['chaos_per_lifeforce_from_divine']:.4f}",
                    row["chaos_for_amount"],
                    row["whole_divine"],
                    row["chaos_left"],
                    row["recommendation"],
                ),
            )

def main() -> None:
    root = tk.Tk()
    app = LifeforceApp(root)
    app.refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
