# CropWise

Farmer-first crop advisory web application: accounts, saved field recommendations, guided demo, Indian weather, fertilizer store, demo delivery orders, tracking and admin view.

1. Copy `.env.example` to `.env` and enter your free OpenWeather key.
2. Install: `pip install -r requirements.txt`.
3. Run: `python app/app.py`, then open `http://127.0.0.1:5000`.

`cropwise.db` is created automatically. The store deliberately does not process payments; it records demo orders for delivery tracking. To validate and improve model artifacts after data changes, run `python src/train_model.py`.
