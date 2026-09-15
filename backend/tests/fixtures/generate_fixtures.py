from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).parent
text = fitz.open()
page = text.new_page()
page.insert_text((50, 70), "Employment contract signed 2026-09-13. Monthly pay 5000 yuan. " * 3)
text.save(root / "text-contract.pdf")

image = Image.new("RGB", (1000, 250), "white")
draw = ImageDraw.Draw(image)
draw.text((30, 80), "Contract date 2026-09-13. Salary 5000 yuan.", fill="black", font=ImageFont.truetype("arial.ttf", 38))
image.save(root / "contract.png")
scan = fitz.open()
page = scan.new_page(width=1000, height=250)
page.insert_image(page.rect, filename=str(root / "contract.png"))
scan.save(root / "scanned-contract.pdf")
