🧠 AI Agent – Domácí úkol (Lekce 2)

Tento projekt obsahuje jednoduchého AI agenta, který:

pracuje se SQLite databází

používá 3 různé tooly

odpovídá přes LLM (OpenAI)

umí vyhledávat produkty, hlídat nízký sklad a měnit počty produktů

Projekt je napsaný v Pythonu a používá function calling.

✔️ Funkce agenta (3 TOOLS)
1️⃣ find_product(name: str)

Najde produkty podle názvu (např. „iPhone“ → najde i „iPhone 15“).

2️⃣ list_low_stock(threshold: int)

Vrátí produkty, které mají méně kusů než uvedený práh (např. < 3).

3️⃣ update_stock(product_id: int, delta: int)

Změní množství produktu na skladě
– může být kladné (naskladnění) nebo záporné (prodej).

🗄️ Databáze

Projekt používá SQLite databázi:

products.db


Tabulka:

Sloupec	Typ	Popis
id	INTEGER PRIMARY KEY	ID produktu
name	TEXT	Název produktu
price	REAL	Cena
stock	INTEGER	Počet kusů na skladě

Databáze se automaticky vytvoří a naplní testovacími daty při prvním spuštění.

🚀 Spuštění projektu
1️⃣ Nainstaluj závislosti
pip install -r requirements.txt

2️⃣ Nastav OpenAI API klíč

Do souboru .env vlož:

OPENAI_API_KEY=sk-xxx

3️⃣ Spusť agenta
python agent.py

💬 Ukázkové dotazy

Můžeš zadat například:

„Najdi iPhone“

„Které produkty mají méně než 3 kusy na skladě?“

„Sniž stock produktu s id 1 o 2 kusy.“

„Kolik stojí MacBook Air M3 a kolik jich máte?“

Agent sám:

vybere správný tool

provede SQL dotaz

dá finální odpověď v češtině

📁 Struktura projektu
homework-2/
│── agent.py
│── requirements.txt
│── README.md
│── .env
└── products.db  (generuje se automaticky)
