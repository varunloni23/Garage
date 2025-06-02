from PIL import Image, ImageDraw, ImageFont
import os

# Create a default product image
img = Image.new('RGB', (300, 300), color=(240, 240, 240))
draw = ImageDraw.Draw(img)

# Add a border
draw.rectangle([(0, 0), (299, 299)], outline=(200, 200, 200), width=2)

# Add text
try:
    font = ImageFont.truetype("Arial", 20)
except IOError:
    font = ImageFont.load_default()

text = "No Image Available"

# Calculate text position to center it
left, top, right, bottom = font.getbbox(text)
text_width = right - left
text_height = bottom - top
position = ((300 - text_width) // 2, (300 - text_height) // 2)

# Draw the text
draw.text(position, text, fill=(100, 100, 100), font=font)

# Ensure directory exists
os.makedirs('static/images/products', exist_ok=True)

# Save the image
img.save('static/images/products/default-product.jpg')

print("Default product image created successfully!") 