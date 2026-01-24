import tweepy
import csv
import random
import os
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap

def load_verses(csv_file='bible_verses.csv'):
    """Load all Bible verses from CSV file"""
    verses = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        verses = list(reader)
    return verses

def load_posted_verses(posted_file='posted_verses.txt'):
    """Load list of already posted verse references"""
    if not os.path.exists(posted_file):
        return set()
    
    with open(posted_file, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_posted_verse(reference, posted_file='posted_verses.txt'):
    """Add a verse reference to the posted list with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d')
    with open(posted_file, 'a', encoding='utf-8') as f:
        f.write(f"{reference}|{timestamp}\n")

def reset_if_new_year(posted_file='posted_verses.txt'):
    """Reset posted verses if it's a new year"""
    if not os.path.exists(posted_file):
        return
    
    # Check the first line for the year
    with open(posted_file, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if '|' in first_line:
            last_year = first_line.split('|')[1].split('-')[0]
            current_year = datetime.now().strftime('%Y')
            
            if last_year != current_year:
                print(f"New year detected! Resetting posted verses from {last_year}")
                # Rename old file as backup
                backup_file = f"posted_verses_{last_year}.txt"
                os.rename(posted_file, backup_file)
                print(f"Backed up to {backup_file}")

def format_tweet(verse):
    """Format verse for Twitter (280 char limit)"""
    reference = verse['reference']
    text = verse['text']
    
    # Format: text - Reference (no quotes)
    tweet = f'{text} - {reference}'
    
    return tweet

def create_gradient(width, height, color1, color2):
    """Create a vertical gradient from color1 to color2"""
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def get_font(size):
    """Try to load a nice font, fallback to default if not available"""
    font_options = [
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        'C:\\Windows\\Fonts\\Arial.ttf',
        'C:\\Windows\\Fonts\\calibri.ttf',
    ]
    
    for font_path in font_options:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    
    return ImageFont.load_default()

def create_verse_image(verse_text, reference, output_path='verse_image.png'):
    """Create an image with verse text and reference on a gradient background"""
    
    width = 1200
    height = 675
    
    # Color schemes
    gradients = [
        ((41, 128, 185), (52, 73, 94)),    # Peaceful blues
        ((255, 94, 77), (200, 70, 120)),   # Warm sunset
        ((106, 17, 203), (37, 117, 252)),  # Purple twilight
        ((34, 139, 34), (0, 100, 0)),      # Forest green
        ((0, 150, 136), (0, 105, 92)),     # Ocean teal
    ]
    
    color1, color2 = random.choice(gradients)
    img = create_gradient(width, height, color1, color2)
    draw = ImageDraw.Draw(img)
    
    verse_font = get_font(48)
    ref_font = get_font(36)
    
    # Text wrapping with padding consideration
    padding = 100  # Left and right padding
    max_chars_per_line = 40  # Reduced to account for padding
    wrapped_text = textwrap.fill(verse_text, width=max_chars_per_line)
    
    # Get text dimensions
    verse_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=verse_font)
    verse_height = verse_bbox[3] - verse_bbox[1]
    
    ref_text = f"- {reference}"
    ref_bbox = draw.textbbox((0, 0), ref_text, font=ref_font)
    ref_height = ref_bbox[3] - ref_bbox[1]
    
    # Calculate vertical positioning (centered)
    total_height = verse_height + 40 + ref_height
    start_y = (height - total_height) // 2
    
    # Draw verse text (centered horizontally with padding)
    verse_x = padding
    verse_width = width - (padding * 2)
    
    # Use anchor='ma' for middle-anchor horizontal centering
    draw.multiline_text(
        (width // 2, start_y),
        wrapped_text,
        font=verse_font,
        fill='white',
        align='center',
        anchor='ma'
    )
    
    # Draw reference (centered below verse)
    ref_y = start_y + verse_height + 40
    draw.text(
        (width // 2, ref_y),
        ref_text,
        font=ref_font,
        fill='white',
        anchor='ma'
    )
    
    img.save(output_path, quality=95)
    return output_path

def select_valid_verse(verses, max_attempts=50):
    """Select a random verse that fits within 280 characters and hasn't been posted this year.
    Uses weighted selection to favor top-ranked verses (earlier in the list)."""
    posted = load_posted_verses()
    
    # Filter out already posted verses
    available_verses = [v for v in verses if v['reference'] not in posted]
    
    if not available_verses:
        print("All verses have been posted this year! Resetting...")
        available_verses = verses
    
    print(f"Available verses: {len(available_verses)} (Posted this year: {len(posted)})")
    
    # Create weights that decay as we go down the list
    # Top 100 get highest weight, then it drops off
    weights = []
    for i in range(len(available_verses)):
        # Exponential decay: weight = e^(-i/200)
        # This heavily favors early verses but still gives chances to later ones
        weight = 2.718 ** (-i / 200)
        weights.append(weight)
    
    for _ in range(max_attempts):
        # Use weighted random choice
        verse = random.choices(available_verses, weights=weights, k=1)[0]
        tweet = format_tweet(verse)
        
        if len(tweet) <= 280:
            return verse, tweet
    
    # If we can't find one after max_attempts, raise an error
    raise Exception(f"Could not find a verse under 280 characters after {max_attempts} attempts")

def post_to_twitter(tweet_text, image_path=None):
    """Post tweet using Twitter API v2 with optional image"""
    
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Authenticate with OAuth 1.0a for media upload
    auth = tweepy.OAuth1UserHandler(
        api_key, api_secret, access_token, access_token_secret
    )
    api_v1 = tweepy.API(auth)
    
    # Upload media if image provided
    media_id = None
    if image_path and os.path.exists(image_path):
        media = api_v1.media_upload(image_path)
        media_id = media.media_id
        print(f"Uploaded image with media_id: {media_id}")
    
    # Post tweet with image
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    if media_id:
        response = client.create_tweet(text=tweet_text, media_ids=[media_id])
    else:
        response = client.create_tweet(text=tweet_text)
    
    return response

def main():
    """Main function to post random Bible verse"""
    try:
        # Check if we need to reset for new year
        reset_if_new_year()
        
        # Load all verses
        print("Loading Bible verses...")
        verses = load_verses()
        print(f"Loaded {len(verses)} verses")
        
        # Select random verse that fits in 280 characters and hasn't been posted
        print("Selecting a verse that fits in 280 characters...")
        verse, tweet_text = select_valid_verse(verses)
        print(f"Selected: {verse['reference']}")
        print(f"Tweet text ({len(tweet_text)} chars):\n{tweet_text}")
        
        # Create image
        print("\nCreating verse image...")
        image_path = create_verse_image(verse['text'], verse['reference'])
        print(f"Image created: {image_path}")
        
        # Post to Twitter with image
        print("\nPosting to Twitter with image...")
        response = post_to_twitter(tweet_text, image_path)
        print(f"Success! Tweet ID: {response.data['id']}")
        
        # Clean up image file
        if os.path.exists(image_path):
            os.remove(image_path)
            print("Cleaned up image file")
        
        # Mark this verse as posted
        save_posted_verse(verse['reference'])
        print(f"Marked {verse['reference']} as posted")
        
    except FileNotFoundError:
        print("Error: bible_verses.csv not found!")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()