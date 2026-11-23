Alsaeed Optics - Flask website with Admin Panel

RUN LOCALLY
1. Extract this folder to C:\AlsaeedOptics (replace the old starter files).
2. Open CMD in C:\AlsaeedOptics.
3. Run: python app.py
4. Open: http://127.0.0.1:5000

FIRST ADMIN SETUP
1. Open http://127.0.0.1:5000/admin/setup
2. Create a username and a strong password (10+ characters).
3. Then sign in at /admin/login.
4. Add products, prices, descriptions and photos from the Admin Panel.

IMPORTANT BEFORE ONLINE HOSTING
- Set a strong random SECRET_KEY environment variable.
- Set SHOP_WHATSAPP to the shop's real number in international digits, e.g. 923001234567.
- Do not use Flask's development server or debug=True for public hosting.
- This starter stores products in SQLite and uploaded images on local disk. For production hosting,
  configure persistent storage or move database and images to durable managed storage.
- Use HTTPS and add CSRF protection/rate limiting before a public production launch.
- Sample product prices and WhatsApp number are placeholders; update them.
