import qrcode

# Replace with your Flask server’s local URL
app_url = "http://10.11.251.52:5000"

# Generate QR code
qr = qrcode.QRCode(
    version=1,
    box_size=10,
    border=5
)
qr.add_data(app_url)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("flask_app_qr.png")

print("✅ QR code generated successfully! Saved as flask_app_qr.png")
