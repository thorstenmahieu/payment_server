BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "currency" (
	"conversion_rate"	REAL NOT NULL,
	"currency_name"	TEXT NOT NULL,
	PRIMARY KEY("currency_name")
);
CREATE TABLE IF NOT EXISTS "payment_requests" (
	"request_id"	INTEGER,
	"requester_account_number"	TEXT NOT NULL,
	"request_amount"	INTEGER NOT NULL,
	"currency"	TEXT NOT NULL,
	"request_time"	REAL NOT NULL,
	"status"	TEXT NOT NULL,
	PRIMARY KEY("request_id" AUTOINCREMENT),
	FOREIGN KEY("currency") REFERENCES "currency"("currency_name"),
	FOREIGN KEY("requester_account_number") REFERENCES "persons"("account_number")
);
CREATE TABLE IF NOT EXISTS "payments" (
	"payment_id"	INTEGER,
	"payment_amount"	REAL NOT NULL,
	"payment_time"	REAL NOT NULL,
	"payment_request_id"	INTEGER UNIQUE,
	"payer_account_number"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	PRIMARY KEY("payment_id" AUTOINCREMENT),
	FOREIGN KEY("currency") REFERENCES "currency"("currency_name"),
	FOREIGN KEY("payer_account_number") REFERENCES "persons"("account_number"),
	FOREIGN KEY("payment_request_id") REFERENCES "payment_requests"("request_id")
);
CREATE TABLE IF NOT EXISTS "persons" (
	"account_number"	TEXT,
	"name"	TEXT ,
	PRIMARY KEY("account_number")
);

-- Seed data
INSERT OR IGNORE INTO "currency" (conversion_rate, currency_name) VALUES (1.0, 'USD');
INSERT OR IGNORE INTO "currency" (conversion_rate, currency_name) VALUES (0.85, 'EUR');
INSERT OR IGNORE INTO "currency" (conversion_rate, currency_name) VALUES (110.0, 'JPY');

INSERT OR IGNORE INTO "persons" (account_number, name) VALUES ('BE84 1234 5678 9012', 'Thorsten');

INSERT OR IGNORE INTO "payment_requests" (request_id, requester_account_number, request_amount, currency, request_time, status) VALUES (1, 'BE84 3410 1235 5486', 100, 'USD', 1756456400, 'pending');

COMMIT;
