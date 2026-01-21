import tweepy
import csv
import random
import os
from pathlib import Path
from datetime import datetime

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
    
    # Basic format: "text" - Reference
    tweet = f'"{text}" - {reference}'
    
    return tweet

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

def post_to_twitter(tweet_text):
    """Post tweet using Twitter API v2"""
    
    # Get credentials from environment variables
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Authenticate
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    # Post tweet
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
        
        # Post to Twitter
        print("\nPosting to Twitter...")
        response = post_to_twitter(tweet_text)
        print(f"Success! Tweet ID: {response.data['id']}")
        
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