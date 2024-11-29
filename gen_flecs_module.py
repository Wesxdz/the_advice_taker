import json
import re

# File paths
input_file = "vital_articles_hierarchy.json"
module_name = "vital"
header_file = f"{module_name}_module.h"
code_file = f"{module_name}_module.c"

# Define categories and subcategories
categories = {
    "People": [
        "Writers_and_journalists", "Artists,_musicians,_and_composers",
        "Entertainers,_directors,_producers,_and_screenwriters",
        "Philosophers,_historians,_and_social_scientists", "Religious_figures",
        "Politicians_and_leaders", "Military_personnel,_revolutionaries,_and_activists",
        "Scientists,_inventors,_and_mathematicians", "Sports_figures", "Miscellaneous"
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

# Read and process the JSON file
with open(input_file, "r", encoding="utf-8") as file:
    vital_articles = json.load(file)

# Extract unique hierarchy strings
unique_hierarchy_strings = set()
for article in vital_articles:
    unique_hierarchy_strings.update(article.get("hierarchy", []))

# Function to sanitize names for valid C++ identifiers
def sanitize_name(name):
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)  # Replace invalid characters with underscores
    sanitized = re.sub(r"__+", "_", sanitized)       # Replace multiple underscores with a single one
    return sanitized.strip("_")                      # Remove leading or trailing underscores

# Combine all unique component names
all_components = set(categories.keys())  # Start with category keys
for subcategories in categories.values():
    all_components.update(subcategories)  # Add subcategories
all_components.update(unique_hierarchy_strings)  # Add hierarchy strings

# Sanitize all component names
sanitized_components = {sanitize_name(name): name for name in all_components}

# Generate header
with open(header_file, "w") as file:
    file.write("#ifndef GENERATED_MAPPINGS_H\n")
    file.write("#define GENERATED_MAPPINGS_H\n\n")

    file.write("#include <flecs.h>\n\n")

    file.write("""
               #ifdef _WIN32
#define VITAL_MODULE_API __declspec(dllexport)
#else
#define VITAL_MODULE_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif\n\n""")

    for sanitized_name, original_name in sanitized_components.items():
        file.write(f'extern ECS_DECLARE(COM_{sanitized_name});\n')

    file.write("\nvoid VitalModuleImport(ecs_world_t* world);\n\n")

    file.write("""VITAL_MODULE_API void VitalModuleImport(ecs_world_t* world);

#ifdef __cplusplus
}
#endif\n""")
    file.write("#endif // GENERATED_MAPPINGS_H")


# Generate C code
with open(code_file, "w") as file:

    # Include required headers
    file.write(f"#include \"{header_file}\"\n\n")

    # Generate forward declaration code
    file.write("\n// Forward declaration \n")
    for sanitized_name, original_name in sanitized_components.items():
        file.write(f'ECS_DECLARE(COM_{sanitized_name});\n')

    file.write("\n// Forward declare article entities\n")
    for article in vital_articles:
        sanitized_title = sanitize_name(article["title"])
        file.write(f'ECS_DECLARE(ENT_{sanitized_title});\n')

    file.write("\nvoid VitalModuleImport(ecs_world_t* world) {\n\n")
    file.write("\tECS_MODULE(world, VitalModule);\n")
    
    # Define components
    for sanitized_name, original_name in sanitized_components.items():
        file.write(f'\tECS_TAG_DEFINE(world, COM_{sanitized_name});\n')

    # Define entities for articles and add components
    file.write("\n\t// Create entities and add components\n")
    for article in vital_articles:
        sanitized_title = sanitize_name(article["title"])
        file.write(f'\tECS_ENTITY_DEFINE(world, ENT_{sanitized_title}, 0);\n')
        
        # Add components for categories, subcategories, and hierarchy
        if "category" in article:
            sanitized_category = sanitize_name(article["category"])
            file.write(f'\tecs_add(world, ENT_{sanitized_title}, COM_{sanitized_category});\n')
        if "subcategory" in article and article["subcategory"] != None:
            sanitized_subcategory = sanitize_name(article["subcategory"])
            file.write(f'\tecs_add(world, ENT_{sanitized_title}, COM_{sanitized_subcategory});\n')
        for hierarchy in article.get("hierarchy", []):
            sanitized_hierarchy = sanitize_name(hierarchy)
            file.write(f'\tecs_add(world, ENT_{sanitized_title}, COM_{sanitized_hierarchy});\n')

    file.write("}\n")
