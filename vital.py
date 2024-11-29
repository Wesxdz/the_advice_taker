import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import json
import time


def extract_articles_with_hierarchy_and_levels(url, category, subcategory):
    # Set up Selenium WebDriver
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service('/usr/bin/chromedriver'), options=options)

    articles = []
    category_hierarchy = []  # Stack to keep track of current hierarchy

    try:
        # Load the page
        driver.get(url)

        excluded_titles = {
            "A", "v", "t", "e", "20", "200", "2,000", "20,000", "100,000",
            "Articles every Wikipedia should have",
            "Top-rated importance articles",
            "Documentation of this template",
            "User:cewbot", "FA", "GA", "B", "C", "FFA", "DGA", "Start", "Stub"
        }

        # Locate the #mw-content-text element
        content = driver.find_element(By.ID, "mw-content-text")
        
        # Find all headings and links within the content area
        headings_and_links = content.find_elements(By.CSS_SELECTOR, "h2, h3, h4, h5, h6, li")

        for element in headings_and_links:
            tag_name = element.tag_name.lower()

            if tag_name.startswith('h') and tag_name[1:].isdigit():
                # Handle headings
                level = int(tag_name[1])  # Extract heading level
                heading_text = element.text.strip()
                # Adjust the hierarchy stack based on the heading level
                while len(category_hierarchy)+1 >= level:
                    category_hierarchy.pop()  # Pop to correct hierarchy level
                category_hierarchy.append(heading_text)  # Push the new heading
            elif tag_name == 'li':
                # Handle list items for articles and levels
                level = 5  # Default level
                # Check for level indicator within the list item
                level_elements = element.find_elements(By.CSS_SELECTOR, "a[href*='Level']")
                if level_elements:
                    # Extract the level from the text, e.g., "Level 4"
                    level_text = level_elements[0].text.strip()
                    if "Level" in level_text:
                        try:
                            level = int(level_text.split("Level")[1].strip())
                        except ValueError:
                            level = 5  # Fallback to default if parsing fails
                
                # Extract the link and title
                links = element.find_elements(By.CSS_SELECTOR, "a[href]")
                for link in links:
                    href = link.get_attribute("href")
                    title = link.text.strip()  # Strip whitespace around the title
                    if (
                        "/wiki/" in href and
                        "File:" not in href and
                        "Wikipedia:" not in href and
                        title and  # Ensure title is not empty
                        title not in excluded_titles  # Exclude unwanted titles
                    ):
                        # Append article with hierarchical categories and level
                        articles.append({
                            "title": title,
                            "category":category,
                            "subcategory":subcategory,
                            "hierarchy": category_hierarchy[:],  # Make a copy of the current hierarchy
                            "level": level
                        })

    finally:
        driver.quit()
    
    return articles


def extract_all_articles_with_hierarchy(categories):
    all_articles = []

    base_url = "https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/Level/5/"
    for category, subcategories in categories.items():
        if not subcategories:  # If there are no subcategories, process the category directly
            url = base_url + category
            print(f"Processing category: {category}")
            articles = extract_articles_with_hierarchy_and_levels(url, category, None)
            all_articles.extend(articles)
        else:  # Process each subcategory
            for subcategory in subcategories:
                url = base_url + category + "/" + subcategory
                print(f"Processing category: {category}, subcategory: {subcategory}")
                articles = extract_articles_with_hierarchy_and_levels(url, category, subcategory)
                all_articles.extend(articles)
    
    return all_articles

if __name__ == "__main__":
    # Define your categories and subcategories here

    # Define categories and subcategories
    categories = {
        "People": [
            "Writers_and_journalists", "Artists,_musicians,_and_composers",
            "Entertainers,_directors,_producers,_and_screenwriters",
            "Philosophers,_historians,_and_social_scientists",
            "Religious_figures", "Politicians_and_leaders",
            "Military_personnel,_revolutionaries,_and_activists",
            "Scientists,_inventors,_and_mathematicians", "Sports_figures",
            "Miscellaneous"
        ],
        "History": [],
        "Geography": ["Physical_geography", "Countries_and_subdivisions", "Cities"],
        "Arts": [],
        "Philosophy_and_religion": [],
        "Everyday_life": ["Everyday_life", "Sports,_games_and_recreation"],
        "Society_and_social_sciences": ["Social_studies", "Politics_and_economics", "Culture"],
        "Biology_and_health_sciences": [
            "Biology,_biochemistry,_anatomy,_and_physiology", "Animals",
            "Plants,_fungi,_and_other_organisms", "Health,_medicine,_and_disease"
        ],
        "Physical_sciences": ["Basics_and_measurement", "Astronomy", "Chemistry", "Earth_science", "Physics"],
        "Technology": [],
        "Mathematics": []
    }

    # Extract articles with categories and subcategories
    articles = extract_all_articles_with_hierarchy(categories)

    # Save to JSON for potential Flecs loading
    with open("vital_articles_hierarchy.json", "w", encoding="utf-8") as file:
        json.dump(articles, file, indent=4)
    
    print(f"Extracted {len(articles)} articles. Saved to vital_articles_hierarchy.json.")

