"""
AI Agent – domácí úkol (AgentBuilder logika, ale v Pythonu)

Agent:
- pracuje se SQLite databází products.db
- má 3 nástroje (tooly):
    1) find_product    – najde produkt podle názvu
    2) list_low_stock  – vypíše produkty s malým skladem
    3) update_stock    – změní počet kusů na skladě
- používá LLM (OpenAI chat completions + function calling)
- odpovídá na dotazy uživatele v češtině
"""

import os
import json
import sqlite3
from typing import Any, Dict, List

from openai import OpenAI

DB_PATH = "products.db"


# ------------------------- DB helper funkce ------------------------- #

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Vytvoří tabulku products a naplní testovacími daty, pokud je prázdná."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
        """
    )

    # zjistit, zda už jsou data
    cur.execute("SELECT COUNT(*) AS cnt FROM products")
    count = cur.fetchone()["cnt"]

    if count == 0:
        cur.executemany(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
            [
                ("iPhone 15", 25990, 5),
                ("MacBook Air M3", 34990, 2),
                ("PlayStation 5", 11990, 10),
                ("Xbox Series X", 11990, 1),
                ("AirPods Pro", 6990, 25),
            ],
        )
        conn.commit()
        print("✅ Databáze vytvořena a naplněna testovacími daty.")
    else:
        print(f"✅ Databáze už obsahuje {count} produktů – nepřepisuji data.")

    conn.close()


# ------------------------- TOOLY (funkce pro LLM) ------------------------- #

def tool_find_product(name: str) -> Dict[str, Any]:
    """Najde produkty podle názvu (LIKE %name%)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, price, stock
        FROM products
        WHERE name LIKE ?
        """,
        (f"%{name}%",),
    )
    rows = cur.fetchall()
    conn.close()

    products: List[Dict[str, Any]] = [
        dict(id=row["id"], name=row["name"], price=row["price"], stock=row["stock"])
        for row in rows
    ]

    return {
        "query": name,
        "count": len(products),
        "products": products,
    }


def tool_list_low_stock(threshold: int) -> Dict[str, Any]:
    """Vrátí produkty, které mají stock < threshold."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, price, stock
        FROM products
        WHERE stock < ?
        ORDER BY stock ASC
        """,
        (threshold,),
    )
    rows = cur.fetchall()
    conn.close()

    products: List[Dict[str, Any]] = [
        dict(id=row["id"], name=row["name"], price=row["price"], stock=row["stock"])
        for row in rows
    ]

    return {
        "threshold": threshold,
        "count": len(products),
        "products": products,
    }


def tool_update_stock(product_id: int, delta: int) -> Dict[str, Any]:
    """
    Upraví počet kusů na skladě (delta může být kladná i záporná).
    Např. delta=-2 => prodaly se 2 kusy.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, price, stock
        FROM products
        WHERE id = ?
        """,
        (product_id,),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": f"Produkt s id={product_id} neexistuje.",
        }

    current_stock = row["stock"]
    new_stock = current_stock + delta

    if new_stock < 0:
        conn.close()
        return {
            "success": False,
            "message": f"Nelze nastavit záporný stock. Aktuální stock je {current_stock}.",
        }

    cur.execute(
        "UPDATE products SET stock = ? WHERE id = ?",
        (new_stock, product_id),
    )
    conn.commit()

    cur.execute(
        """
        SELECT id, name, price, stock
        FROM products
        WHERE id = ?
        """,
        (product_id,),
    )
    updated = cur.fetchone()
    conn.close()

    return {
        "success": True,
        "message": "Stock byl úspěšně aktualizován.",
        "product": {
            "id": updated["id"],
            "name": updated["name"],
            "price": updated["price"],
            "stock": updated["stock"],
        },
    }


# ------------------------- LLM + function calling ------------------------- #

def run_agent(user_question: str) -> str:
    """
    Pošle dotaz do LLM, nechá LLM vybrat tool(e),
    provede tool a vrátí finální odpověď.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    functions = [
        {
            "name": "find_product",
            "description": "Najde produkty podle názvu v databázi products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Část nebo celý název produktu, např. 'iPhone'.",
                    }
                },
                "required": ["name"],
            },
        },
        {
            "name": "list_low_stock",
            "description": "Vrátí produkty s nízkým skladem (stock < threshold).",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "Prahová hodnota množství na skladě, např. 3.",
                    }
                },
                "required": ["threshold"],
            },
        },
        {
            "name": "update_stock",
            "description": "Aktualizuje počet kusů na skladě pro daný produkt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "ID produktu v databázi.",
                    },
                    "delta": {
                        "type": "integer",
                        "description": "Změna množství: -2 = prodaly se 2 kusy.",
                    },
                },
                "required": ["product_id", "delta"],
            },
        },
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "Jsi asistent e-shopu pracující se SQLite databází. "
                "Používej tooly find_product, list_low_stock a update_stock podle potřeby. "
                "Vždy odpovídej česky, stručně a jasně."
            ),
        },
        {"role": "user", "content": user_question},
    ]

    # první volání – model může chtít použít funkci
    first = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        functions=functions,
        function_call="auto",
    )

    msg = first.choices[0].message

    # model nevolá funkci → odpovíme přímo
    if not msg.function_call:
        return msg.content or ""

    # model chce použít tool
    fn_name = msg.function_call.name
    raw_args = msg.function_call.arguments or "{}"

    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        return "Model poslal nevalidní argumenty."

    print(f"🔧 LLM volá funkci: {fn_name}({args})")

    if fn_name == "find_product":
        result = tool_find_product(args["name"])
    elif fn_name == "list_low_stock":
        result = tool_list_low_stock(args["threshold"])
    elif fn_name == "update_stock":
        result = tool_update_stock(args["product_id"], args["delta"])
    else:
        result = {"error": "Neznámá funkce."}

    # přidáme odpověď toolu
    messages.append(
        {
            "role": "function",
            "name": fn_name,
            "content": json.dumps(result, ensure_ascii=False),
        }
    )

    # finální odpověď
    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    return final.choices[0].message.content or ""


# ------------------------- CLI entrypoint ------------------------- #

def main():
    init_db()

    print("AI Agent – 3 tooly (find_product, list_low_stock, update_stock)")
    print("Zadej dotaz typu:")
    print("- 'Najdi iPhone'")
    print("- 'Které produkty mají méně než 3 kusy?'")
    print("- 'Sniž stock produktu s id 1 o 2 kusy.'\n")

    user_q = input("Tvůj dotaz: ")

    answer = run_agent(user_q)
    print("\n💬 Odpověď agenta:\n")
    print(answer)


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Nastav OPENAI_API_KEY v .env souboru.")
    main()
