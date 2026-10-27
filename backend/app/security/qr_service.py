import io
import base64
import qrcode

def generate_qr_data_uri(content: str) -> str:
    """
    Generates a secure, standalone base64 Data URI PNG for the given content.
    Never includes secrets or refresh tokens.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F1E38", back_color="#FFFFFF")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"
