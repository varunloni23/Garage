from PIL import Image, ImageDraw, ImageFont
import os

# Create products directory if it doesn't exist
os.makedirs('static/images/products', exist_ok=True)

# List of products
products = [
    'motor-oil-5w30',
    'motor-oil-10w40',
    'transmission-fluid',
    'coolant',
    'oil-filter',
    'air-filter',
    'cabin-filter',
    'fuel-filter',
    'brake-pads',
    'brake-rotors',
    'brake-fluid',
    'brake-calipers'
]

# Generate a simple placeholder image for each product
for product in products:
    # Create a new image with a white background
    img = Image.new('RGB', (300, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Add a border
    draw.rectangle([(0, 0), (299, 299)], outline=(200, 200, 200), width=2)
    
    # Add product name
    product_name = product.replace('-', ' ').title()
    
    # Try to use a system font, fallback to default if not available
    try:
        font = ImageFont.truetype("Arial", 20)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    # Using the newer method for text size calculation
    left, top, right, bottom = font.getbbox(product_name)
    text_width = right - left
    text_height = bottom - top
    position = ((300 - text_width) // 2, (300 - text_height) // 2)
    
    # Draw the text
    draw.text(position, product_name, fill=(0, 0, 0), font=font)
    
    # Save the image
    img.save(f'static/images/products/{product}.jpg')

print("Product images generated successfully!") 