import pandas as pd

# ---------- STEP 1: Load Dataset ----------
df = pd.read_json(
    "/kaggle/input/datasets/seungyeonhan1/recipe-dataset-with-images-tags-and-ratings/recipes_images.json"
)

# ---------- STEP 2: Flatten Tags ----------
def extract_flat_tags(tag_dict):
    if isinstance(tag_dict, dict):
        tags = []
        for v in tag_dict.values():
            tags.extend(v)
        return tags
    return []

df["flat_tags"] = df["tags"].apply(extract_flat_tags)

# ---------- STEP 3: Dish Type ----------
BAD_FIRST_TAGS = {"quick", "easy", "weeknight meals"}

def get_dish_type(row):
    tag_dict = row["tags"]
    flat_tags = row["flat_tags"]

    # Use original type if available
    if isinstance(tag_dict, dict) and "type" in tag_dict:
        if len(tag_dict["type"]) > 0:
            return tag_dict["type"][0].lower()

    # Otherwise use first meaningful tag
    for tag in flat_tags:
        tag_lower = tag.lower()
        if tag_lower not in BAD_FIRST_TAGS:
            return tag_lower

    return "dish"

df["dish_type"] = df.apply(get_dish_type, axis=1)

# ---------- STEP 4: Build desc_embedding_text ----------
def build_text(row):
    desc = row["description"]
    tags = row["flat_tags"]
    dish_type = row["dish_type"]

    # Clean description
    if not isinstance(desc, str):
        desc = ""

    # Lowercase tags
    tags_lower = [t.lower() for t in tags]

    # PROFILE (all tags)
    profile = " ".join(tags_lower)

    # "includes" sentence
    if len(tags_lower) > 0:
        includes = ", ".join(tags_lower[:-1])
        if len(tags_lower) > 1:
            includes += " and " + tags_lower[-1]
        else:
            includes = tags_lower[0]
        includes_sentence = f"This recipe includes {includes}."
    else:
        includes_sentence = ""

    # FINAL TEXT
    return (
        f"dish type: {dish_type}. "
        f"profile: {profile}. "
        f"description: {desc} "
        f"{includes_sentence}"
    ).strip()

df["desc_embedding_text"] = df.apply(build_text, axis=1)


# ---------- STEP 5: Keep Only Required Columns ----------
df_final = df[["title", "desc_embedding_text"]].dropna()


# ---------- STEP 6: Save as JSON ----------
df_final.to_json(
    "/kaggle/working/recipe_embeddings.json",
    orient="records",
    indent=2,
    force_ascii=False
)

print("JSON file created: /kaggle/working/recipe_embeddings.json")