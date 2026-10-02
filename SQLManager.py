#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import cmd
import sys
import os
import time
import csv


class SQLShell(cmd.Cmd):
    intro = (
        "=== SQL Database Management System ===\n"
        "Type 'help' or '?' for commands, 'help <cmd>' for details.\n"
    )
    prompt = "sql> "

    def __init__(self, db_path=":memory:"):
        super().__init__()
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.in_transaction = False
        self._connect(db_path)

    def _connect(self, db_path):
        try:
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.db_path = db_path
            self.prompt = f"sql[{os.path.basename(db_path)}]> "
            print(f"Connected to: {db_path}")
        except Exception as e:
            print(f"Connection error: {e}")

    def _print_rows(self, rows, columns):
        if not rows:
            print("(empty result set)")
            return
        data = [[("" if v is None else str(v)) for v in row] for row in rows]
        widths = [len(c) for c in columns]
        for row in data:
            for i, v in enumerate(row):
                widths[i] = max(widths[i], len(v))
        line = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
        sep = "-+-".join("-" * w for w in widths)
        print(line)
        print(sep)
        for row in data:
            print(" | ".join(v.ljust(widths[i]) for i, v in enumerate(row)))
        print(f"\n({len(rows)} row(s))")

    def default(self, line):
        if not line.strip():
            return
        low = line.strip().lower()
        if low in ("exit", "quit", "q"):
            return self.do_exit("")
        try:
            self.cursor.execute(line)
            if self.cursor.description:
                cols = [d[0] for d in self.cursor.description]
                self._print_rows(self.cursor.fetchall(), cols)
            else:
                print(f"Query OK, {self.cursor.rowcount} row(s) affected.")
            if not self.in_transaction:
                self.conn.commit()
        except Exception as e:
            print(f"Error: {e}")

    def do_open(self, arg):
        """open <db_path> : Open or switch to another database file."""
        if not arg.strip():
            print("Usage: open <db_path>")
            return
        self._connect(arg.strip())

    def do_attach(self, arg):
        """attach <db_path> AS <alias> : Attach another database."""
        try:
            self.cursor.execute(f"ATTACH DATABASE {arg};")
            print("Database attached.")
        except Exception as e:
            print(f"Error: {e}")

    def do_detach(self, arg):
        """detach <alias> : Detach an attached database."""
        try:
            self.cursor.execute(f"DETACH DATABASE {arg.strip()};")
            print("Database detached.")
        except Exception as e:
            print(f"Error: {e}")

    def do_backup(self, arg):
        """backup <target_path> : Back up the current database."""
        if not arg.strip():
            print("Usage: backup <target_path>")
            return
        target = arg.strip()
        try:
            dst = sqlite3.connect(target)
            with dst:
                self.conn.backup(dst)
            dst.close()
            print(f"Database backed up to '{target}'")
        except Exception as e:
            print(f"Error: {e}")

    def do_info(self, arg):
        """info : Show basic information about the current database."""
        try:
            self.cursor.execute("SELECT sqlite_version();")
            ver = self.cursor.fetchone()[0]
            self.cursor.execute("PRAGMA page_count;")
            pages = self.cursor.fetchone()[0]
            self.cursor.execute("PRAGMA page_size;")
            size = self.cursor.fetchone()[0]
            print(f"DB file   : {self.db_path}")
            print(f"SQLite    : {ver}")
            print(f"Size      : {pages * size / 1024:.2f} KB")
        except Exception as e:
            print(f"Error: {e}")

    def do_tables(self, arg):
        """tables : List all tables."""
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            rows = self.cursor.fetchall()
            if rows:
                print("Tables:")
                for r in rows:
                    print(f"  - {r[0]}")
            else:
                print("No tables found.")
        except Exception as e:
            print(f"Error: {e}")

    def do_views(self, arg):
        """views : List all views."""
        try:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;"
            )
            rows = self.cursor.fetchall()
            if rows:
                print("Views:")
                for r in rows:
                    print(f"  - {r[0]}")
            else:
                print("No views found.")
        except Exception as e:
            print(f"Error: {e}")

    def do_indexes(self, arg):
        """indexes [table] : List indexes."""
        try:
            if arg.strip():
                self.cursor.execute(f"PRAGMA index_list({arg.strip()});")
            else:
                self.cursor.execute(
                    "SELECT tbl_name, name FROM sqlite_master "
                    "WHERE type='index' ORDER BY tbl_name, name;"
                )
            self._print_rows(
                self.cursor.fetchall(),
                [d[0] for d in self.cursor.description],
            )
        except Exception as e:
            print(f"Error: {e}")

    def do_schema(self, arg):
        """schema <table> : Show the table structure."""
        if not arg.strip():
            print("Usage: schema <table_name>")
            return
        try:
            self.cursor.execute(f"PRAGMA table_info({arg.strip()});")
            cols = self.cursor.fetchall()
            if cols:
                print(f"Schema for table '{arg.strip()}':")
                print(f"{'cid':<5}{'name':<20}{'type':<15}{'notnull':<10}{'default':<15}{'pk':<5}")
                print("-" * 70)
                for c in cols:
                    print(
                        f"{c[0]:<5}{str(c[1]):<20}{str(c[2]):<15}"
                        f"{str(c[3]):<10}{str(c[4]):<15}{str(c[5]):<5}"
                    )
            else:
                print(f"Table '{arg.strip()}' not found.")
        except Exception as e:
            print(f"Error: {e}")

    def do_ddl(self, arg):
        """ddl <table> : Show the CREATE statement for a table."""
        if not arg.strip():
            print("Usage: ddl <table_name>")
            return
        try:
            self.cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                (arg.strip(),),
            )
            row = self.cursor.fetchone()
            print(row[0] if row else "Not found.")
        except Exception as e:
            print(f"Error: {e}")

    def do_count(self, arg):
        """count <table> : Count rows in a table."""
        if not arg.strip():
            print("Usage: count <table_name>")
            return
        try:
            self.cursor.execute(f"SELECT COUNT(*) FROM {arg.strip()};")
            print(f"{arg.strip()}: {self.cursor.fetchone()[0]} row(s)")
        except Exception as e:
            print(f"Error: {e}")

    def do_begin(self, arg):
        """begin : Start a transaction."""
        try:
            self.cursor.execute("BEGIN;")
            self.in_transaction = True
            print("Transaction started.")
        except Exception as e:
            print(f"Error: {e}")

    def do_commit(self, arg):
        """commit : Commit the current transaction."""
        try:
            self.conn.commit()
            self.in_transaction = False
            print("Transaction committed.")
        except Exception as e:
            print(f"Error: {e}")

    def do_rollback(self, arg):
        """rollback : Roll back the current transaction."""
        try:
            self.conn.rollback()
            self.in_transaction = False
            print("Transaction rolled back.")
        except Exception as e:
            print(f"Error: {e}")

    def do_export(self, arg):
        """export <table> <csv_path> : Export a table to CSV."""
        parts = arg.split()
        if len(parts) < 2:
            print("Usage: export <table> <csv_path>")
            return
        table, path = parts[0], parts[1]
        try:
            self.cursor.execute(f"SELECT * FROM {table};")
            cols = [d[0] for d in self.cursor.description]
            rows = self.cursor.fetchall()
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(cols)
                w.writerows([list(r) for r in rows])
            print(f"Exported {len(rows)} row(s) to '{path}'")
        except Exception as e:
            print(f"Error: {e}")

    def do_import(self, arg):
        """import <table> <csv_path> : Import CSV into an existing table."""
        parts = arg.split()
        if len(parts) < 2:
            print("Usage: import <table> <csv_path>")
            return
        table, path = parts[0], parts[1]
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                placeholders = ",".join(["?"] * len(header))
                sql = f"INSERT INTO {table} ({','.join(header)}) VALUES ({placeholders})"
                n = 0
                for row in reader:
                    self.cursor.execute(sql, row)
                    n += 1
            self.conn.commit()
            print(f"Imported {n} row(s) into '{table}'")
        except Exception as e:
            print(f"Error: {e}")

    def do_pragmas(self, arg):
        """pragmas : Show common PRAGMA settings."""
        for p in ("journal_mode", "synchronous", "foreign_keys", "encoding"):
            try:
                self.cursor.execute(f"PRAGMA {p};")
                print(f"{p:<16}: {self.cursor.fetchone()[0]}")
            except Exception as e:
                print(f"{p:<16}: error - {e}")

    def do_set(self, arg):
        """set <pragma> <value> : Change a PRAGMA setting."""
        parts = arg.split()
        if len(parts) < 2:
            print("Usage: set <pragma> <value>")
            return
        try:
            self.cursor.execute(f"PRAGMA {parts[0]}={parts[1]};")
            print(f"{parts[0]} set to {parts[1]}")
        except Exception as e:
            print(f"Error: {e}")

    def do_timer(self, arg):
        """timer : Toggle statement timing."""
        self._timer = not getattr(self, "_timer", False)
        print("Timer: " + ("on" if self._timer else "off"))

    def do_history(self, arg):
        """history : Show statements executed in this session."""
        hist = getattr(self, "_history", [])
        for i, h in enumerate(hist, 1):
            print(f"{i:>3}. {h}")

    def do_exit(self, arg):
        """exit : Exit the shell."""
        try:
            self.conn.close()
        except Exception:
            pass
        print("Goodbye!")
        return True

    def do_EOF(self, arg):
        """EOF : Exit on Ctrl+D."""
        print()
        return self.do_exit("")

    def onecmd(self, line):
        if line.strip():
            self._history = getattr(self, "_history", [])
            self._history.append(line)
        if getattr(self, "_timer", False):
            t0 = time.time()
            r = super().onecmd(line)
            print(f"[{time.time() - t0:.3f}s]")
            return r
        return super().onecmd(line)


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
    SQLShell(db).cmdloop()
